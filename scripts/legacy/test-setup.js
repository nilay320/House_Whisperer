// Test script to verify API setup before deployment

async function testChat() {
  console.log('Testing chat endpoint...');
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

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let result = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      result += decoder.decode(value);
    }

    console.log('Chat response received:', result.substring(0, 200) + '...');
    return true;
  } catch (error) {
    console.error('Chat test failed:', error);
    return false;
  }
}

async function testIngest() {
  console.log('\nTesting ingest endpoint...');
  try {
    const response = await fetch('http://localhost:3000/api/ingest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        documents: [{
          source: "Test Document",
          section: "Test",
          content: "This is a test document for verification."
        }],
        reset: false
      }),
    });

    const result = await response.json();
    console.log('Ingest response:', result);
    return result.success;
  } catch (error) {
    console.error('Ingest test failed:', error);
    return false;
  }
}

async function runTests() {
  console.log('Starting API tests...\n');
  
  // Test ingest first
  const ingestOk = await testIngest();
  
  if (ingestOk) {
    // Wait a bit for indexing
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test chat
    const chatOk = await testChat();
    
    if (chatOk) {
      console.log('\n✅ All tests passed! Ready for deployment.');
    } else {
      console.log('\n❌ Chat test failed. Check your setup.');
    }
  } else {
    console.log('\n❌ Ingest test failed. Check your Qdrant configuration.');
  }
}

// Run tests
runTests();