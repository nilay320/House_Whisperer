const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

async function testChatAPI() {
  console.log('🧪 Testing Chat API...\n');
  
  try {
    const response = await fetch('http://localhost:3000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'What is the required clearance for electrical panels?',
        sessionId: 'test-session'
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    console.log('✅ API responded');
    
    // Handle streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              process.stdout.write(data.content);
              fullResponse += data.content;
            }
            if (data.sources) {
              console.log('\n\n📚 Sources:');
              data.sources.forEach(s => {
                console.log(`• ${s.source} (${(s.score * 100).toFixed(1)}%)`);
              });
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
    
    console.log('\n\n🎉 Chat API is working!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testChatAPI();