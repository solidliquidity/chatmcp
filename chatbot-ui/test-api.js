const { mcpClient } = require('./lib/mcp/mcp-client.ts');

async function testMCPAPI() {
  try {
    console.log('Testing MCP API connection...');
    
    // Test connection
    await mcpClient.connect();
    console.log('Connected to MCP server');
    
    // Test listing tools
    const tools = await mcpClient.listTools();
    console.log('Available tools:', tools);
    
    // Test calling a tool
    if (tools.length > 0) {
      const result = await mcpClient.callTool('scrape_url', {
        url: 'https://example.com'
      });
      console.log('Tool result:', result);
    }
    
    await mcpClient.disconnect();
    console.log('Disconnected from MCP server');
    
  } catch (error) {
    console.error('Error testing MCP API:', error);
  }
}

testMCPAPI();