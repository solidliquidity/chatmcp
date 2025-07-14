import { firecrawlMCPClient } from './mcp-client';

// MCP Tools for LLM function calling
export async function getMCPTools() {
  try {
    await firecrawlMCPClient.connect();
    const tools = await firecrawlMCPClient.listTools();
    
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
    return [];
  }
}

export async function executeMCPTool(toolName: string, args: any): Promise<any> {
  try {
    await firecrawlMCPClient.connect();
    const result = await firecrawlMCPClient.callTool(toolName, args);
    return result;
  } catch (error) {
    console.error('Error executing MCP tool:', error);
    throw error;
  }
}