const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

async function testAPI() {
  try {
    console.log('🧪 Testing CommonJS API function...');
    
    // Require the handler function
    const handler = require('../api/chat.js');
    
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
    console.error('❌ CommonJS API test failed:', error);
    console.error('Error details:', error.message);
  }
}

testAPI();