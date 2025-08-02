import { QdrantClient } from '@qdrant/js-client-rest';
import { OpenAI } from 'openai';
import { encoding_for_model } from 'tiktoken';

// Initialize clients
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';
const EMBEDDING_MODEL = 'text-embedding-3-small';
const CHAT_MODEL = 'gpt-4o-mini';

// Helper function to count tokens
function countTokens(text, model = 'gpt-4o-mini') {
  const encoding = encoding_for_model(model);
  const tokens = encoding.encode(text);
  encoding.free();
  return tokens.length;
}

// Generate embeddings
async function getEmbedding(text) {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: text,
  });
  return response.data[0].embedding;
}

// Basic RAG retrieval
async function retrieve(query, limit = 5) {
  const queryEmbedding = await getEmbedding(query);
  
  const searchResult = await qdrant.search(COLLECTION_NAME, {
    vector: queryEmbedding,
    limit,
    with_payload: true,
  });
  
  return searchResult.map(result => ({
    content: result.payload.content,
    source: result.payload.source,
    score: result.score,
  }));
}

// Generate response using retrieved context
async function generate(query, context) {
  const systemPrompt = `You are an expert home inspector assistant with deep knowledge of InterNACHI standards, NCHILB regulations, and best practices. Answer questions accurately based on the provided context from official inspection standards and regulations.`;
  
  const userPrompt = `Context from inspection standards:
${context.map((c, i) => `[${i+1}] ${c.content}\nSource: ${c.source}`).join('\n\n')}

Question: ${query}

Provide a clear, accurate answer based on the context above. If the context doesn't contain enough information, say so.`;

  const response = await openai.chat.completions.create({
    model: CHAT_MODEL,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ],
    temperature: 0.3,
    stream: true,
  });
  
  return response;
}

// Main handler
export default async function handler(req, res) {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, sessionId } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Message is required' });
    }

    // Retrieve relevant context
    const context = await retrieve(message);
    
    // Generate streaming response
    const stream = await generate(message, context);
    
    // Set up SSE headers for streaming
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });

    // Stream the response
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        res.write(`data: ${JSON.stringify({ content })}\n\n`);
      }
    }
    
    // Send sources at the end
    res.write(`data: ${JSON.stringify({ 
      sources: context.map(c => ({ source: c.source, score: c.score })),
      done: true 
    })}\n\n`);
    
    res.end();
  } catch (error) {
    console.error('RAG Error:', error);
    res.status(500).json({ 
      error: 'An error occurred processing your request',
      details: error.message 
    });
  }
}