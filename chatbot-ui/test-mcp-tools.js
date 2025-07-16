const { getMCPTools, generateSystemPrompt } = require('./lib/mcp/mcp-integration.ts');

async function testMCPTools() {
  console.log('Testing MCP tools discovery...');
  
  try {
    const tools = await getMCPTools();
    console.log('✅ MCP tools discovered:', tools.length);
    
    // Show Excel-specific tools
    const excelTools = tools.filter(tool => tool.function.name.includes('excel'));
    console.log('📊 Excel tools found:', excelTools.length);
    
    excelTools.forEach(tool => {
      console.log(`  - ${tool.function.name}: ${tool.function.description}`);
    });
    
    // Test system prompt generation
    const systemPrompt = generateSystemPrompt(tools);
    console.log('\n📝 System prompt generated:', systemPrompt.length > 0 ? 'Yes' : 'No');
    
    if (systemPrompt.length > 0) {
      console.log('First 500 chars of system prompt:');
      console.log(systemPrompt.substring(0, 500) + '...');
    }
    
  } catch (error) {
    console.error('❌ Error testing MCP tools:', error);
  }
}

testMCPTools();