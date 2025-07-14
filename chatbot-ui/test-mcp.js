const { spawn } = require('child_process');

// Test if firecrawl-mcp command works
console.log('Testing firecrawl-mcp command...');

const testProcess = spawn('npx', ['firecrawl-mcp', '--help'], {
  stdio: 'inherit',
  env: {
    ...process.env,
    FIRECRAWL_API_KEY: process.env.FIRECRAWL_API_KEY || 'fc-0639cae8dcc44ae2a93f7064937dd097'
  }
});

testProcess.on('close', (code) => {
  console.log(`Process exited with code ${code}`);
});

testProcess.on('error', (error) => {
  console.error('Error starting process:', error);
});

setTimeout(() => {
  testProcess.kill();
  console.log('Test completed');
}, 5000);