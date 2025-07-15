import { firecrawlMCPClient } from './mcp-client';
import { multiMCPClient } from './multi-mcp-client';

// MCP Tools for LLM function calling
export async function getMCPTools() {
  try {
    // Connect to all MCP servers
    await multiMCPClient.connectAll();
    
    // Get tools from all connected servers
    const tools = await multiMCPClient.getAllTools();
    
    // Convert MCP tools to OpenAI function format
    return tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema
      }
    }));
  } catch (error) {
    console.error('Error getting MCP tools:', error);
    
    // Fallback to original firecrawl client
    try {
      await firecrawlMCPClient.connect();
      const tools = await firecrawlMCPClient.listTools();
      
      return tools.map(tool => ({
        type: 'function',
        function: {
          name: `firecrawl_${tool.name}`,
          description: tool.description,
          parameters: tool.inputSchema
        }
      }));
    } catch (fallbackError) {
      console.error('Fallback MCP client also failed:', fallbackError);
      return [];
    }
  }
}

// Generate comprehensive system prompt for LLM
export function generateSystemPrompt(tools: any[]): string {
  if (tools.length === 0) {
    return '';
  }

  const toolNames = tools.map(tool => tool.function?.name || tool.name).join(', ');
  
  // Group tools by server for better organization
  const firecrawlTools = tools.filter(tool => {
    const name = tool.function?.name || tool.name;
    return name.startsWith('firecrawl_');
  });
  
  const columbiaLakeTools = tools.filter(tool => {
    const name = tool.function?.name || tool.name;
    return name.startsWith('columbia-lake-agents_');
  });
  
  const excelTools = tools.filter(tool => {
    const name = tool.function?.name || tool.name;
    return name.startsWith('excel-mcp_');
  });

  let systemPrompt = `You are an AI assistant with access to specialized tools. You have access to these tools: ${toolNames}.

IMPORTANT: When a user asks for information or actions that can be performed by your available tools, you MUST use the appropriate tool functions rather than declining or explaining limitations. Always attempt to use the relevant tool first before providing a general response.

Available tool categories:`;

  if (firecrawlTools.length > 0) {
    systemPrompt += `\n\nWEB SCRAPING & RESEARCH TOOLS (firecrawl_*):
- Use for: Website cloning, content extraction, web research, data scraping
- Examples: ${firecrawlTools.map(t => t.function?.name || t.name).join(', ')}`;
  }

  if (columbiaLakeTools.length > 0) {
    systemPrompt += `\n\nBUSINESS INTELLIGENCE TOOLS (columbia-lake-agents_*):
- Use for: Company analysis, Excel file processing, portfolio management, health monitoring
- Examples: ${columbiaLakeTools.map(t => t.function?.name || t.name).join(', ')}`;
  }

  if (excelTools.length > 0) {
    systemPrompt += `\n\nEXCEL MANIPULATION TOOLS (excel-mcp_*):
- Use for: Excel file operations, data reading/writing, formula application, workbook management
- Examples: ${excelTools.map(t => t.function?.name || t.name).join(', ')}`;
  }

  systemPrompt += `\n\nSPECIFIC GUIDELINES:
- For Excel operations: Use excel-mcp_* tools for direct Excel file manipulation
- For company data: Use columbia-lake-agents_* tools for business intelligence
- For web research: Use firecrawl_* tools for web scraping and content extraction
- Always use the most specific tool available for the task
- If multiple tools could apply, choose the one that best fits the user's intent`;

  return systemPrompt;
}

export async function executeMCPTool(toolName: string, args: any): Promise<any> {
  try {
    // Check if this is a multi-MCP tool (has server prefix)
    if (toolName.includes('_')) {
      const result = await multiMCPClient.executeTool(toolName, args);
      return result;
    }
    
    // Fallback to original firecrawl client for backward compatibility
    await firecrawlMCPClient.connect();
    const result = await firecrawlMCPClient.callTool(toolName, args);
    return result;
  } catch (error) {
    console.error('Error executing MCP tool:', error);
    throw error;
  }
}

// New function to get connection status for all servers
export async function getMCPStatus(): Promise<Record<string, boolean>> {
  try {
    const connectedServers = multiMCPClient.getConnectedServers();
    const status: Record<string, boolean> = {};
    
    // Check multi-MCP servers
    for (const serverName of ['firecrawl', 'columbia-lake-agents']) {
      status[serverName] = connectedServers.includes(serverName);
    }
    
    return status;
  } catch (error) {
    console.error('Error getting MCP status:', error);
    return {};
  }
}

// New function to get tools from specific server
export async function getServerTools(serverName: string): Promise<any[]> {
  try {
    const tools = await multiMCPClient.getServerTools(serverName);
    
    return tools.map(tool => ({
      type: 'function',
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema
      }
    }));
  } catch (error) {
    console.error(`Error getting tools from ${serverName}:`, error);
    return [];
  }
}