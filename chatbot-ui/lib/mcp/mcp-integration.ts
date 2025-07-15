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