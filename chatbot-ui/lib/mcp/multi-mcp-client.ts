import { spawn, ChildProcess } from 'child_process';
import path from 'path';

interface MCPServerConfig {
  command: string;
  args: string[];
  cwd: string;
  env: Record<string, string>;
}

interface MCPClientConfig {
  [serverName: string]: MCPServerConfig;
}

export class MCPClient {
  private process: ChildProcess | null = null;
  private isConnected = false;
  private requestId = 1;
  private pendingRequests = new Map<number, { resolve: Function; reject: Function }>();
  private serverName: string;
  private config: MCPServerConfig;

  constructor(serverName: string, config: MCPServerConfig) {
    this.serverName = serverName;
    this.config = config;
  }

  async connect(): Promise<void> {
    if (this.isConnected) return;

    return new Promise((resolve, reject) => {
      console.log(`Starting MCP client for ${this.serverName}`);
      
      this.process = spawn(this.config.command, this.config.args, {
        stdio: 'pipe',
        cwd: this.config.cwd,
        env: {
          ...process.env,
          ...this.config.env
        }
      });

      let initialized = false;

      // Handle stderr for initialization messages
      this.process.stderr?.on('data', (data) => {
        const output = data.toString();
        console.log(`MCP Server (${this.serverName}) stderr:`, output);
        
        // Check for various initialization indicators
        if ((output.includes('initialized') || 
             output.includes('Excel MCP Server') || 
             output.includes('Stdio mode')) && !initialized) {
          initialized = true;
          this.setupMessageHandling();
          this.isConnected = true;
          resolve();
        }
      });

      // Handle stdout for initialization messages (some servers output here)
      this.process.stdout?.on('data', (data) => {
        const output = data.toString();
        console.log(`MCP Server (${this.serverName}) stdout:`, output);
        
        // Check for various initialization indicators
        if ((output.includes('initialized') || 
             output.includes('Excel MCP Server') || 
             output.includes('Stdio mode')) && !initialized) {
          initialized = true;
          this.setupMessageHandling();
          this.isConnected = true;
          resolve();
        }
      });

      // Setup message handling immediately for stdio transport
      this.setupMessageHandling();

      // Handle process errors
      this.process.on('error', (error) => {
        console.error(`MCP process error (${this.serverName}):`, error);
        if (!initialized) reject(error);
      });

      this.process.on('close', (code) => {
        console.log(`MCP process (${this.serverName}) closed with code ${code}`);
        this.isConnected = false;
        this.process = null;
      });

      // Initialize the server
      setTimeout(() => {
        if (this.process?.stdin) {
          const initRequest = {
            jsonrpc: '2.0',
            id: this.requestId++,
            method: 'initialize',
            params: {
              protocolVersion: '2024-11-05',
              capabilities: {
                tools: {}
              },
              clientInfo: {
                name: 'chatbot-ui',
                version: '1.0.0'
              }
            }
          };
          console.log(`Sending initialization request to ${this.serverName}:`, initRequest);
          this.process.stdin.write(JSON.stringify(initRequest) + '\n');
          
          // For stdio transport, assume initialization is successful after sending request
          if (this.serverName === 'excel-mcp') {
            setTimeout(() => {
              if (!initialized) {
                console.log(`MCP Server ${this.serverName} initialized (stdio transport)`);
                initialized = true;
                this.isConnected = true;
                resolve();
              }
            }, 1000);
          }
        }
      }, 1000);

      // Timeout if server doesn't start
      setTimeout(() => {
        if (!initialized) {
          console.error(`MCP server ${this.serverName} failed to initialize within timeout`);
          console.error(`Process stdout: ${this.process?.stdout ? 'available' : 'not available'}`);
          console.error(`Process stderr: ${this.process?.stderr ? 'available' : 'not available'}`);
          reject(new Error(`MCP server ${this.serverName} failed to initialize within timeout`));
        }
      }, 30000); // Increased timeout to 30 seconds
    });
  }

  private setupMessageHandling(): void {
    if (!this.process?.stdout) return;

    let buffer = '';

    this.process.stdout.on('data', (data) => {
      buffer += data.toString();
      
      // Process complete JSON messages
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        
        if (line) {
          try {
            const message = JSON.parse(line);
            this.handleMessage(message);
          } catch (error) {
            console.error(`Failed to parse MCP message (${this.serverName}):`, line, error);
          }
        }
      }
    });
  }

  private handleMessage(message: any): void {
    console.log(`MCP Server (${this.serverName}) received message:`, message);
    
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject } = this.pendingRequests.get(message.id)!;
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message || 'MCP request failed'));
      } else {
        resolve(message.result);
      }
    }
    
    // Handle initialization response
    if (message.method === 'initialize' || (message.result && message.result.serverInfo)) {
      console.log(`MCP Server (${this.serverName}) initialized successfully`);
      this.isConnected = true;
    }
  }

  private async sendRequest(method: string, params?: any): Promise<any> {
    if (!this.process?.stdin) {
      throw new Error(`MCP client (${this.serverName}) not connected`);
    }

    const id = this.requestId++;
    const request = {
      jsonrpc: '2.0',
      id,
      method,
      ...(params && { params })
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });

      this.process!.stdin!.write(JSON.stringify(request) + '\n');

      // Timeout after 45 seconds
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`MCP request timeout (${this.serverName})`));
        }
      }, 45000);
    });
  }

  async disconnect(): Promise<void> {
    if (!this.isConnected) return;

    this.process?.kill();
    this.process = null;
    this.isConnected = false;
    this.pendingRequests.clear();
  }

  async listTools(): Promise<any[]> {
    console.log(`Requesting tools from ${this.serverName}...`);
    try {
      // Try without parameters first
      let response;
      try {
        response = await this.sendRequest('tools/list');
      } catch (error) {
        // If that fails, try with empty parameters
        console.log(`Retrying tools/list with parameters for ${this.serverName}...`);
        response = await this.sendRequest('tools/list', {});
      }
      console.log(`Tools response from ${this.serverName}:`, response);
      return response.tools || [];
    } catch (error) {
      console.error(`Error getting tools from ${this.serverName}:`, error);
      
      // For Excel MCP server, if tools/list fails, return empty array
      // This allows the server to connect but without tool discovery
      if (this.serverName === 'excel-mcp') {
        console.log(`Excel MCP server doesn't support tools/list, continuing without tool discovery`);
        return [];
      }
      
      return [];
    }
  }

  async callTool(name: string, args: any): Promise<any> {
    console.log(`[DEBUG] MCPClient.callTool - tool: ${name}, args:`, JSON.stringify(args, null, 2));
    const requestParams = {
      name,
      arguments: args
    };
    console.log(`[DEBUG] Sending tools/call request:`, JSON.stringify(requestParams, null, 2));
    const response = await this.sendRequest('tools/call', requestParams);
    return response;
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  getServerName(): string {
    return this.serverName;
  }
}

export class MultiMCPClient {
  private clients = new Map<string, MCPClient>();
  private toolsCache = new Map<string, any[]>();
  private lastToolsRefresh = 0;
  private readonly TOOLS_CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  constructor() {
    this.loadConfiguration();
  }

  private loadConfiguration(): void {
    try {
      // Load Firecrawl MCP configuration
      const firecrawlConfig: MCPServerConfig = {
        command: 'firecrawl-mcp',
        args: [],
        cwd: process.cwd(),
        env: {
          FIRECRAWL_API_KEY: process.env.FIRECRAWL_API_KEY || ''
        }
      };

      // Load Columbia Lake agents configuration  
      const agentsConfig: MCPServerConfig = {
        command: '/Users/solidliquidity/.pyenv/versions/3.11.6/bin/python3',
        args: ['mcp_server.py'],
        cwd: path.join(process.cwd(), '..', 'agents'),
        env: {
          GOOGLE_API_KEY: process.env.GOOGLE_API_KEY || '',
          DB_HOST: process.env.DB_HOST || 'localhost',
          DB_PORT: process.env.DB_PORT || '5432',
          DB_NAME: process.env.DB_NAME || 'columbia_lake',
          DB_USER: process.env.DB_USER || 'postgres',
          DB_PASSWORD: process.env.DB_PASSWORD || '',
          EMAIL_ADDRESS: process.env.EMAIL_ADDRESS || '',
          EMAIL_PASSWORD: process.env.EMAIL_PASSWORD || '',
          SMTP_SERVER: process.env.SMTP_SERVER || 'smtp.office365.com',
          SMTP_PORT: process.env.SMTP_PORT || '587'
        }
      };

      // Load Excel MCP server configuration
      const excelConfig: MCPServerConfig = {
        command: 'python3',
        args: ['-m', 'excel_mcp', 'stdio'],
        cwd: path.join(process.cwd(), '..', 'excel-mcp-server'),
        env: {
          EXCEL_FILES_PATH: process.env.EXCEL_FILES_PATH || path.join(process.cwd(), '..', 'excel-files')
        }
      };

      // Register clients
      this.clients.set('firecrawl', new MCPClient('firecrawl', firecrawlConfig));
      this.clients.set('columbia-lake-agents', new MCPClient('columbia-lake-agents', agentsConfig));
      this.clients.set('excel-mcp', new MCPClient('excel-mcp', excelConfig));

    } catch (error) {
      console.error('Failed to load MCP configuration:', error);
    }
  }

  async connectAll(): Promise<void> {
    const connectionPromises = Array.from(this.clients.entries()).map(async ([name, client]) => {
      try {
        await client.connect();
        console.log(`✅ Connected to MCP server: ${name}`);
      } catch (error) {
        console.error(`❌ Failed to connect to MCP server ${name}:`, error);
      }
    });

    await Promise.allSettled(connectionPromises);
  }

  async disconnectAll(): Promise<void> {
    const disconnectionPromises = Array.from(this.clients.values()).map(client => 
      client.disconnect()
    );

    await Promise.allSettled(disconnectionPromises);
    this.toolsCache.clear();
  }

  async getAllTools(): Promise<any[]> {
    const now = Date.now();
    
    // Return cached tools if still fresh
    if (now - this.lastToolsRefresh < this.TOOLS_CACHE_TTL && this.toolsCache.size > 0) {
      const allTools: any[] = [];
      for (const tools of this.toolsCache.values()) {
        allTools.push(...tools);
      }
      return allTools;
    }

    // Refresh tools from all servers
    const allTools: any[] = [];
    
    for (const [serverName, client] of this.clients.entries()) {
      if (client.getConnectionStatus()) {
        let tools: any[] = [];
        
        try {
          // For Excel MCP server, always use manual discovery since it may not support tools/list properly
          if (serverName === 'excel-mcp') {
            console.log(`Using manually discovered tools for ${serverName} (forced override)`);
            tools = this.getExcelMCPServerTools();
          } else {
            tools = await client.listTools();
            console.log(`Raw tools from ${serverName}:`, tools.length, tools);
          }
        } catch (error) {
          // For Excel MCP server, use manually discovered tools
          if (serverName === 'excel-mcp') {
            console.log(`Using manually discovered tools for ${serverName} (fallback)`);
            tools = this.getExcelMCPServerTools();
          } else {
            console.error(`Failed to get tools from ${serverName}:`, error);
            continue; // Skip this server and continue with others
          }
        }
        
        // Add server prefix to tool names to avoid conflicts
        const prefixedTools = tools.map(tool => ({
          ...tool,
          name: `${serverName}_${tool.name}`,
          serverName
        }));
        
        this.toolsCache.set(serverName, prefixedTools);
        allTools.push(...prefixedTools);
      }
    }

    this.lastToolsRefresh = now;
    return allTools;
  }

  async executeTool(toolName: string, args: any): Promise<any> {
    // Parse server name from tool name
    const parts = toolName.split('_');
    const serverName = parts[0];
    const actualToolName = parts.slice(1).join('_');

    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`Unknown MCP server: ${serverName}`);
    }

    if (!client.getConnectionStatus()) {
      throw new Error(`MCP server ${serverName} is not connected`);
    }

    try {
      console.log(`[DEBUG] Executing tool ${toolName} with args:`, JSON.stringify(args, null, 2));
      console.log(`[DEBUG] Actual tool name: ${actualToolName}`);
      
      // Special handling for excel-mcp tools - use fallback for now
      if (serverName === 'excel-mcp') {
        console.log(`[DEBUG] Using fallback implementation for excel-mcp tool: ${actualToolName}`);
        if (actualToolName === 'search_excel_files') {
          return await this.executeExcelSearchFallback(args);
        } else if (actualToolName === 'get_common_excel_locations') {
          return await this.executeExcelLocationsFallback();
        } else if (actualToolName === 'read_data_from_excel') {
          return await this.executeExcelReadFallback(args);
        } else if (actualToolName === 'get_workbook_metadata') {
          return await this.executeExcelMetadataFallback(args);
        } else {
          throw new Error(`Excel MCP tool ${actualToolName} not implemented in fallback`);
        }
      }
      
      return await client.callTool(actualToolName, args);
    } catch (error) {
      console.error(`Error executing tool ${toolName}:`, error);
      throw error;
    }
  }

  getConnectedServers(): string[] {
    return Array.from(this.clients.entries())
      .filter(([_, client]) => client.getConnectionStatus())
      .map(([name, _]) => name);
  }

  async getServerTools(serverName: string): Promise<any[]> {
    const client = this.clients.get(serverName);
    if (!client || !client.getConnectionStatus()) {
      return [];
    }

    try {
      return await client.listTools();
    } catch (error) {
      console.error(`Failed to get tools from ${serverName}:`, error);
      
      // For Excel MCP server, return manually discovered tools
      if (serverName === 'excel-mcp') {
        return this.getExcelMCPServerTools();
      }
      
      return [];
    }
  }

  private getExcelMCPServerTools(): any[] {
    // Manually discovered tools from the Excel MCP server code
    const excelTools = [
      {
        name: 'apply_formula',
        description: 'Apply Excel formula to cell with verification',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            cell: { type: 'string', description: 'Cell reference' },
            formula: { type: 'string', description: 'Excel formula to apply' }
          },
          required: ['filepath', 'sheet_name', 'cell', 'formula']
        }
      },
      {
        name: 'validate_formula_syntax',
        description: 'Validate Excel formula syntax without applying it',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            cell: { type: 'string', description: 'Cell reference' },
            formula: { type: 'string', description: 'Excel formula to validate' }
          },
          required: ['filepath', 'sheet_name', 'cell', 'formula']
        }
      },
      {
        name: 'read_data_from_excel',
        description: 'Read data from Excel worksheet with cell metadata including validation rules',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell (default A1)' },
            end_cell: { type: 'string', description: 'Ending cell (optional)' },
            preview_only: { type: 'boolean', description: 'Whether to return preview only' }
          },
          required: ['filepath', 'sheet_name']
        }
      },
      {
        name: 'write_data_to_excel',
        description: 'Write data to Excel worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            data: { type: 'array', description: 'List of lists containing data to write' },
            start_cell: { type: 'string', description: 'Cell to start writing to (default A1)' }
          },
          required: ['filepath', 'sheet_name', 'data']
        }
      },
      {
        name: 'create_workbook',
        description: 'Create new Excel workbook',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path where to create workbook' }
          },
          required: ['filepath']
        }
      },
      {
        name: 'create_worksheet',
        description: 'Create new worksheet in workbook',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name for the new worksheet' }
          },
          required: ['filepath', 'sheet_name']
        }
      },
      {
        name: 'create_chart',
        description: 'Create charts and graphs in Excel',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            data_range: { type: 'string', description: 'Data range for chart' },
            chart_type: { type: 'string', description: 'Type of chart' },
            target_cell: { type: 'string', description: 'Target cell for chart' },
            title: { type: 'string', description: 'Chart title' },
            x_axis: { type: 'string', description: 'X-axis label' },
            y_axis: { type: 'string', description: 'Y-axis label' }
          },
          required: ['filepath', 'sheet_name', 'data_range', 'chart_type', 'target_cell']
        }
      },
      {
        name: 'create_pivot_table',
        description: 'Create pivot table in Excel worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            data_range: { type: 'string', description: 'Data range for pivot table' },
            rows: { type: 'array', description: 'Row fields' },
            values: { type: 'array', description: 'Value fields' },
            columns: { type: 'array', description: 'Column fields (optional)' },
            agg_func: { type: 'string', description: 'Aggregation function (default mean)' }
          },
          required: ['filepath', 'sheet_name', 'data_range', 'rows', 'values']
        }
      },
      {
        name: 'create_table',
        description: 'Create Excel table',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            data_range: { type: 'string', description: 'Data range for table' },
            table_name: { type: 'string', description: 'Name for the table (optional)' },
            table_style: { type: 'string', description: 'Table style (default TableStyleMedium9)' }
          },
          required: ['filepath', 'sheet_name', 'data_range']
        }
      },
      {
        name: 'copy_worksheet',
        description: 'Copy worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            source_sheet: { type: 'string', description: 'Source worksheet name' },
            target_sheet: { type: 'string', description: 'Target worksheet name' }
          },
          required: ['filepath', 'source_sheet', 'target_sheet']
        }
      },
      {
        name: 'delete_worksheet',
        description: 'Delete worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet to delete' }
          },
          required: ['filepath', 'sheet_name']
        }
      },
      {
        name: 'rename_worksheet',
        description: 'Rename worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            old_name: { type: 'string', description: 'Current worksheet name' },
            new_name: { type: 'string', description: 'New worksheet name' }
          },
          required: ['filepath', 'old_name', 'new_name']
        }
      },
      {
        name: 'get_workbook_metadata',
        description: 'Get metadata about workbook including sheets and ranges',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            include_ranges: { type: 'boolean', description: 'Whether to include range information' }
          },
          required: ['filepath']
        }
      },
      {
        name: 'merge_cells',
        description: 'Merge a range of cells',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell of range' },
            end_cell: { type: 'string', description: 'Ending cell of range' }
          },
          required: ['filepath', 'sheet_name', 'start_cell', 'end_cell']
        }
      },
      {
        name: 'unmerge_cells',
        description: 'Unmerge a previously merged range of cells',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell of range' },
            end_cell: { type: 'string', description: 'Ending cell of range' }
          },
          required: ['filepath', 'sheet_name', 'start_cell', 'end_cell']
        }
      },
      {
        name: 'get_merged_cells',
        description: 'Get merged cells in a worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' }
          },
          required: ['filepath', 'sheet_name']
        }
      },
      {
        name: 'copy_range',
        description: 'Copy cell range',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            source_start: { type: 'string', description: 'Source start cell' },
            source_end: { type: 'string', description: 'Source end cell' },
            target_start: { type: 'string', description: 'Target start cell' },
            target_sheet: { type: 'string', description: 'Target worksheet (optional)' }
          },
          required: ['filepath', 'sheet_name', 'source_start', 'source_end', 'target_start']
        }
      },
      {
        name: 'delete_range',
        description: 'Delete cell range',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell' },
            end_cell: { type: 'string', description: 'Ending cell' },
            shift_direction: { type: 'string', description: 'Shift direction (up/down/left/right)' }
          },
          required: ['filepath', 'sheet_name', 'start_cell', 'end_cell']
        }
      },
      {
        name: 'validate_excel_range',
        description: 'Validate Excel range',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell' },
            end_cell: { type: 'string', description: 'Ending cell (optional)' }
          },
          required: ['filepath', 'sheet_name', 'start_cell']
        }
      },
      {
        name: 'search_excel_files',
        description: 'Search for Excel files on the filesystem. Use "." for current directory or absolute paths like "/Users/username" instead of "~".',
        inputSchema: {
          type: 'object',
          properties: {
            search_path: { 
              type: 'string', 
              description: 'Directory to search in (default: current directory ".")',
              default: '.'
            },
            filename_pattern: { 
              type: 'string', 
              description: 'Pattern to match (default: "*.xlsx", supports *.xls, *.xlsm)',
              default: '*.xlsx'
            },
            include_subdirs: { 
              type: 'boolean', 
              description: 'Whether to search subdirectories recursively (default: true)',
              default: true
            },
            max_results: { 
              type: 'number', 
              description: 'Maximum number of results to return (default: 50)',
              default: 50
            }
          },
          required: []
        }
      },
      {
        name: 'get_common_excel_locations',
        description: 'Get common locations where Excel files are typically stored',
        inputSchema: {
          type: 'object',
          properties: {},
          required: []
        }
      },
      {
        name: 'get_data_validation_info',
        description: 'Get all data validation rules in a worksheet',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' }
          },
          required: ['filepath', 'sheet_name']
        }
      },
      {
        name: 'format_range',
        description: 'Apply formatting to a range of cells',
        inputSchema: {
          type: 'object',
          properties: {
            filepath: { type: 'string', description: 'Path to Excel file' },
            sheet_name: { type: 'string', description: 'Name of worksheet' },
            start_cell: { type: 'string', description: 'Starting cell' },
            end_cell: { type: 'string', description: 'Ending cell (optional)' },
            bold: { type: 'boolean', description: 'Make text bold' },
            italic: { type: 'boolean', description: 'Make text italic' },
            underline: { type: 'boolean', description: 'Make text underlined' },
            font_size: { type: 'number', description: 'Font size' },
            font_color: { type: 'string', description: 'Font color' },
            bg_color: { type: 'string', description: 'Background color' },
            border_style: { type: 'string', description: 'Border style' },
            border_color: { type: 'string', description: 'Border color' },
            number_format: { type: 'string', description: 'Number format' },
            alignment: { type: 'string', description: 'Text alignment' },
            wrap_text: { type: 'boolean', description: 'Wrap text' },
            merge_cells: { type: 'boolean', description: 'Merge cells' }
          },
          required: ['filepath', 'sheet_name', 'start_cell']
        }
      }
    ];

    return excelTools;
  }

  private async executeExcelSearchFallback(args: any): Promise<any> {
    console.log('[DEBUG] Executing Excel search fallback with args:', args);
    
    const searchPath = args.search_path || '~';
    const filenamePattern = args.filename_pattern || '*.xlsx';
    const includeSubdirs = args.include_subdirs !== false;
    const maxResults = args.max_results || 50;
    
    // Expand home directory
    const expandedPath = searchPath === '~' || searchPath === 'home' || searchPath === 'home directory' 
      ? require('os').homedir() 
      : searchPath.startsWith('~/') 
        ? require('path').join(require('os').homedir(), searchPath.slice(2))
        : searchPath;
    
    try {
      const fs = require('fs');
      const path = require('path');
      const glob = require('glob');
      
      // Build search pattern
      const pattern = includeSubdirs 
        ? path.join(expandedPath, '**', filenamePattern)
        : path.join(expandedPath, filenamePattern);
      
      console.log(`[DEBUG] Searching with pattern: ${pattern}`);
      
      // Find files
      const foundFiles: any[] = [];
      const files = glob.sync(pattern, { maxFiles: maxResults });
      
      for (const filepath of files) {
        try {
          const stat = fs.statSync(filepath);
          const fileInfo = {
            filepath: filepath,
            filename: path.basename(filepath),
            directory: path.dirname(filepath),
            size_bytes: stat.size,
            size_mb: Math.round(stat.size / (1024 * 1024) * 100) / 100,
            modified: stat.mtime.getTime() / 1000,
            modified_readable: stat.mtime.toISOString().slice(0, 19).replace('T', ' ')
          };
          foundFiles.push(fileInfo);
        } catch (error) {
          console.warn(`Error getting info for ${filepath}:`, error);
          continue;
        }
      }
      
      // Sort by modification time (newest first)
      foundFiles.sort((a, b) => b.modified - a.modified);
      
      const result = {
        search_path: expandedPath,
        pattern: filenamePattern,
        include_subdirs: includeSubdirs,
        total_found: foundFiles.length,
        files: foundFiles
      };
      
      console.log(`[DEBUG] Excel search fallback found ${foundFiles.length} files`);
      return result;
      
    } catch (error) {
      console.error('[DEBUG] Excel search fallback error:', error);
      return {
        error: `Search failed: ${error.message}`,
        search_path: expandedPath,
        pattern: filenamePattern,
        total_found: 0,
        files: []
      };
    }
  }

  private async executeExcelLocationsFallback(): Promise<any> {
    const os = require('os');
    const path = require('path');
    const fs = require('fs');
    
    const homeDir = os.homedir();
    const platform = os.platform();
    const commonLocations: any[] = [];
    
    let locations: string[] = [];
    if (platform === 'darwin') { // macOS
      locations = [
        path.join(homeDir, 'Desktop'),
        path.join(homeDir, 'Documents'),
        path.join(homeDir, 'Downloads'),
        path.join(homeDir, 'Library', 'CloudStorage')
      ];
    } else if (platform === 'win32') { // Windows
      locations = [
        path.join(homeDir, 'Desktop'),
        path.join(homeDir, 'Documents'),
        path.join(homeDir, 'Downloads'),
        path.join(homeDir, 'OneDrive')
      ];
    } else { // Linux
      locations = [
        path.join(homeDir, 'Desktop'),
        path.join(homeDir, 'Documents'),
        path.join(homeDir, 'Downloads')
      ];
    }
    
    for (const location of locations) {
      try {
        if (fs.existsSync(location)) {
          const files = fs.readdirSync(location);
          const excelCount = files.filter((f: string) => 
            f.endsWith('.xlsx') || f.endsWith('.xls') || f.endsWith('.xlsm')
          ).length;
          
          commonLocations.push({
            path: location,
            exists: true,
            excel_files_count: excelCount
          });
        } else {
          commonLocations.push({
            path: location,
            exists: false,
            excel_files_count: 0
          });
        }
      } catch (error) {
        commonLocations.push({
          path: location,
          exists: true,
          excel_files_count: 'Permission denied'
        });
      }
    }
    
    return {
      os: platform,
      home_directory: homeDir,
      common_locations: commonLocations
    };
  }

  private async executeExcelReadFallback(args: any): Promise<any> {
    console.log('[DEBUG] Executing Excel read fallback with args:', args);
    
    try {
      const XLSX = require('xlsx');
      const path = require('path');
      const fs = require('fs');
      
      let filepath = args.filepath;
      const sheetName = args.sheet_name || 'Sheet1';
      const startCell = args.start_cell || 'A1';
      const previewOnly = args.preview_only || false;
      
      // Expand home directory in filepath
      if (filepath.startsWith('~')) {
        filepath = path.join(require('os').homedir(), filepath.slice(1));
      }
      
      // Check if file exists
      if (!fs.existsSync(filepath)) {
        return {
          error: `File not found: ${filepath}`,
          filepath: filepath,
          sheet_name: sheetName
        };
      }
      
      console.log(`[DEBUG] Reading Excel file: ${filepath}, sheet: ${sheetName}`);
      
      // Read the Excel file
      const workbook = XLSX.readFile(filepath);
      
      // Check if sheet exists
      if (!workbook.SheetNames.includes(sheetName)) {
        return {
          error: `Sheet '${sheetName}' not found in workbook`,
          filepath: filepath,
          available_sheets: workbook.SheetNames
        };
      }
      
      const worksheet = workbook.Sheets[sheetName];
      
      // Convert to JSON with cell addresses
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
        header: 1, 
        defval: null,
        raw: false 
      });
      
      // Convert to cell format similar to what the MCP server would return
      const cells: any[] = [];
      const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1');
      
      for (let row = range.s.r; row <= Math.min(range.e.r, previewOnly ? 20 : range.e.r); row++) {
        for (let col = range.s.c; col <= range.e.c; col++) {
          const cellAddr = XLSX.utils.encode_cell({ r: row, c: col });
          const cell = worksheet[cellAddr];
          
          if (cell) {
            cells.push({
              address: cellAddr,
              value: cell.v,
              type: cell.t,
              format: cell.z || null,
              row: row + 1,
              column: XLSX.utils.encode_col(col)
            });
          }
        }
      }
      
      const result = {
        filepath: filepath,
        sheet_name: sheetName,
        range: worksheet['!ref'] || 'A1',
        total_rows: range.e.r + 1,
        total_columns: range.e.c + 1,
        preview_only: previewOnly,
        cells: cells,
        data: jsonData.slice(0, previewOnly ? 20 : jsonData.length)
      };
      
      console.log(`[DEBUG] Excel read fallback found ${cells.length} cells`);
      return result;
      
    } catch (error) {
      console.error('[DEBUG] Excel read fallback error:', error);
      return {
        error: `Failed to read Excel file: ${error.message}`,
        filepath: args.filepath,
        sheet_name: args.sheet_name
      };
    }
  }

  private async executeExcelMetadataFallback(args: any): Promise<any> {
    console.log('[DEBUG] Executing Excel metadata fallback with args:', args);
    
    try {
      const XLSX = require('xlsx');
      const path = require('path');
      const fs = require('fs');
      
      let filepath = args.filepath;
      const includeRanges = args.include_ranges || false;
      
      // Expand home directory in filepath
      if (filepath.startsWith('~')) {
        filepath = path.join(require('os').homedir(), filepath.slice(1));
      }
      
      // Check if file exists
      if (!fs.existsSync(filepath)) {
        return {
          error: `File not found: ${filepath}`,
          filepath: filepath
        };
      }
      
      console.log(`[DEBUG] Reading Excel metadata: ${filepath}`);
      
      // Read the Excel file
      const workbook = XLSX.readFile(filepath);
      
      // Get file stats
      const stats = fs.statSync(filepath);
      
      // Build sheet information
      const sheets = workbook.SheetNames.map(name => {
        const worksheet = workbook.Sheets[name];
        const range = worksheet['!ref'] || 'A1';
        const decodedRange = XLSX.utils.decode_range(range);
        
        const sheetInfo: any = {
          name: name,
          range: range,
          rows: decodedRange.e.r + 1,
          columns: decodedRange.e.c + 1
        };
        
        if (includeRanges) {
          // Add more detailed range information
          sheetInfo.start_cell = XLSX.utils.encode_cell(decodedRange.s);
          sheetInfo.end_cell = XLSX.utils.encode_cell(decodedRange.e);
          sheetInfo.used_range = range;
        }
        
        return sheetInfo;
      });
      
      const result = {
        filepath: filepath,
        filename: path.basename(filepath),
        file_size: stats.size,
        modified: stats.mtime.toISOString(),
        sheets: sheets,
        total_sheets: sheets.length,
        include_ranges: includeRanges
      };
      
      console.log(`[DEBUG] Excel metadata fallback found ${sheets.length} sheets`);
      return result;
      
    } catch (error) {
      console.error('[DEBUG] Excel metadata fallback error:', error);
      return {
        error: `Failed to read Excel metadata: ${error.message}`,
        filepath: args.filepath
      };
    }
  }
}

// Singleton instance
export const multiMCPClient = new MultiMCPClient();