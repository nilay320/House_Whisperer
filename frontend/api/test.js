// Simple test API function to check if basic functionality works
module.exports = async function handler(req, res) {
  console.log('Test function called');
  console.log('Environment check:');
  console.log('OPENAI_API_KEY exists:', !!process.env.OPENAI_API_KEY);
  console.log('QDRANT_URL exists:', !!process.env.QDRANT_URL);
  
  res.setHeader('Content-Type', 'application/json');
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    const { message } = req.body || {};
    
    res.status(200).json({ 
      success: true, 
      message: `Echo: ${message}`,
      env_check: {
        openai: !!process.env.OPENAI_API_KEY,
        qdrant: !!process.env.QDRANT_URL
      }
    });
    
  } catch (error) {
    console.error('Test API error:', error);
    res.status(500).json({ 
      error: 'Test failed',
      details: error.message 
    });
  }
};