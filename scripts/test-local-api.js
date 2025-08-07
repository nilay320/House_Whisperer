const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

// Test environment variables
console.log('Environment variables:');
console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? 'SET' : 'NOT SET');
console.log('QDRANT_URL:', process.env.QDRANT_URL ? 'SET' : 'NOT SET');
console.log('QDRANT_API_KEY:', process.env.QDRANT_API_KEY ? 'SET' : 'NOT SET');

// Test API function directly
async function testAPI() {
  try {
    console.log('\n🧪 Testing API function directly...');
    
    // Import the handler function
    const { default: handler } = await import('../api/chat.js');
    
    // Mock request and response objects
    const req = {
      method: 'POST',
      body: {
        message: 'What clearance is required for electrical panels?',
        sessionId: 'test-session'
      }
    };
    
    const res = {
      setHeader: () => {},
      writeHead: () => {},
      write: (data) => console.log('Response chunk:', data),
      end: () => console.log('Response ended'),
      status: (code) => ({
        json: (data) => console.log('Response:', code, data),
        end: () => console.log('Response ended with status:', code)
      })
    };
    
    await handler(req, res);
    
  } catch (error) {
    console.error('❌ Direct API test failed:', error);
    console.error('Error details:', error.message);
    console.error('Stack:', error.stack);
  }
}

// Test HTTP request to local server
async function testHTTP() {
  try {
    console.log('\n🌐 Testing HTTP request to local server...');
    
    const response = await fetch('http://localhost:3001/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'What clearance is required for electrical panels?',
        sessionId: 'test-session'
      }),
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers));
    
    const text = await response.text();
    console.log('Response body:', text);
    
  } catch (error) {
    console.error('❌ HTTP test failed:', error);
  }
}

async function runTests() {
  await testAPI();
  await testHTTP();
}

runTests();