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
        console.log(`MCP Server (${this.serverName}):`, output);
        
        if (output.includes('initialized') && !initialized) {
          initialized = true;
          this.setupMessageHandling();
          this.isConnected = true;
          resolve();
        }
      });

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
              capabilities: {},
              clientInfo: {
                name: 'chatbot-ui',
                version: '1.0.0'
              }
            }
          };
          this.process.stdin.write(JSON.stringify(initRequest) + '\n');
        }
      }, 1000);

      // Timeout if server doesn't start
      setTimeout(() => {
        if (!initialized) {
          reject(new Error(`MCP server ${this.serverName} failed to initialize within timeout`));
        }
      }, 15000);
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
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject } = this.pendingRequests.get(message.id)!;
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message || 'MCP request failed'));
      } else {
        resolve(message.result);
      }
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
    const response = await this.sendRequest('tools/list');
    return response.tools || [];
  }

  async callTool(name: string, args: any): Promise<any> {
    const response = await this.sendRequest('tools/call', {
      name,
      arguments: args
    });
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

      // Register clients
      this.clients.set('firecrawl', new MCPClient('firecrawl', firecrawlConfig));
      this.clients.set('columbia-lake-agents', new MCPClient('columbia-lake-agents', agentsConfig));

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
      try {
        if (client.getConnectionStatus()) {
          const tools = await client.listTools();
          
          // Add server prefix to tool names to avoid conflicts
          const prefixedTools = tools.map(tool => ({
            ...tool,
            name: `${serverName}_${tool.name}`,
            serverName
          }));
          
          this.toolsCache.set(serverName, prefixedTools);
          allTools.push(...prefixedTools);
        }
      } catch (error) {
        console.error(`Failed to get tools from ${serverName}:`, error);
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
      return [];
    }
  }
}

// Singleton instance
export const multiMCPClient = new MultiMCPClient();