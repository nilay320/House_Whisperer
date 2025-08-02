import { QdrantClient } from '@qdrant/js-client-rest';
import { OpenAI } from 'openai';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';

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
const EMBEDDING_DIMENSION = 1536;

// Text splitter for chunking
const textSplitter = new RecursiveCharacterTextSplitter({
  chunkSize: 1000,
  chunkOverlap: 200,
  separators: ['\n\n', '\n', '.', '!', '?', ';', ':', ' ', ''],
});

// Generate embeddings for multiple texts
async function getEmbeddings(texts) {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: texts,
  });
  return response.data.map(d => d.embedding);
}

// Create or recreate collection
async function initializeCollection() {
  try {
    // Check if collection exists
    const collections = await qdrant.getCollections();
    const exists = collections.collections.some(c => c.name === COLLECTION_NAME);
    
    if (exists) {
      // Delete existing collection for fresh start
      await qdrant.deleteCollection(COLLECTION_NAME);
    }
    
    // Create new collection
    await qdrant.createCollection(COLLECTION_NAME, {
      vectors: {
        size: EMBEDDING_DIMENSION,
        distance: 'Cosine',
      },
    });
    
    return true;
  } catch (error) {
    console.error('Error initializing collection:', error);
    return false;
  }
}

// Process and ingest documents
async function ingestDocuments(documents) {
  const points = [];
  let id = 0;
  
  for (const doc of documents) {
    // Split document into chunks
    const chunks = await textSplitter.splitText(doc.content);
    
    // Process in batches of 100
    for (let i = 0; i < chunks.length; i += 100) {
      const batch = chunks.slice(i, i + 100);
      const embeddings = await getEmbeddings(batch);
      
      // Create points for Qdrant
      for (let j = 0; j < batch.length; j++) {
        points.push({
          id: id++,
          vector: embeddings[j],
          payload: {
            content: batch[j],
            source: doc.source,
            section: doc.section || 'General',
            chunk_index: i + j,
            total_chunks: chunks.length,
          },
        });
      }
    }
  }
  
  // Upload to Qdrant in batches
  const batchSize = 100;
  for (let i = 0; i < points.length; i += batchSize) {
    const batch = points.slice(i, i + batchSize);
    await qdrant.upsert(COLLECTION_NAME, {
      wait: true,
      points: batch,
    });
  }
  
  return points.length;
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
    const { documents, reset = false } = req.body;
    
    if (!documents || !Array.isArray(documents)) {
      return res.status(400).json({ error: 'Documents array is required' });
    }

    // Initialize collection if requested
    if (reset) {
      const initialized = await initializeCollection();
      if (!initialized) {
        return res.status(500).json({ error: 'Failed to initialize collection' });
      }
    }

    // Ingest documents
    const totalChunks = await ingestDocuments(documents);
    
    res.status(200).json({ 
      success: true,
      message: `Ingested ${documents.length} documents into ${totalChunks} chunks`,
      collection: COLLECTION_NAME,
    });
  } catch (error) {
    console.error('Ingestion Error:', error);
    res.status(500).json({ 
      error: 'An error occurred during ingestion',
      details: error.message 
    });
  }
}