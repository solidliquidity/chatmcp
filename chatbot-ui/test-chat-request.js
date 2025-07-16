const fetch = require('node-fetch');

async function testChatRequest() {
  try {
    const response = await fetch('http://localhost:3001/api/chat/tools', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chatSettings: {
          model: 'gpt-4'
        },
        messages: [
          {
            role: 'user',
            content: 'Can you help me with an Excel file?'
          }
        ],
        selectedTools: []
      })
    });
    
    console.log('Response status:', response.status);
    if (!response.ok) {
      console.error('Response error:', await response.text());
    } else {
      console.log('Response OK');
    }
    
  } catch (error) {
    console.error('Request error:', error.message);
  }
}

testChatRequest();