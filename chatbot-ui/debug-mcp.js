// Simple debugging script to check if Excel MCP tools are being discovered
console.log('Starting MCP debug...');

async function testMCPConnection() {
  try {
    // Import the multi-MCP client
    const { multiMCPClient } = await import('./lib/mcp/multi-mcp-client.ts');
    
    console.log('Connecting to all MCP servers...');
    await multiMCPClient.connectAll();
    
    console.log('Getting all tools...');
    const tools = await multiMCPClient.getAllTools();
    
    console.log('Total tools found:', tools.length);
    
    // Filter for Excel tools
    const excelTools = tools.filter(tool => tool.name && tool.name.includes('excel-mcp'));
    console.log('Excel MCP tools found:', excelTools.length);
    
    excelTools.forEach(tool => {
      console.log(`  - ${tool.name}: ${tool.description}`);
    });
    
    // Check connection status
    const connectedServers = multiMCPClient.getConnectedServers();
    console.log('Connected servers:', connectedServers);
    
    process.exit(0);
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

testMCPConnection();