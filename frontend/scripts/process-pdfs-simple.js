const fs = require('fs');
const path = require('path');

// Load environment variables from .env.local
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });
const { QdrantClient } = require('@qdrant/js-client-rest');
const { OpenAI } = require('openai');

// Simple PDF text extraction using pdf-parse
const pdf = require('pdf-parse');

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

// Simple text chunking
function chunkText(text, chunkSize = 1000, overlap = 200) {
  const chunks = [];
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
  
  let currentChunk = '';
  
  for (const sentence of sentences) {
    if (currentChunk.length + sentence.length > chunkSize && currentChunk.length > 0) {
      chunks.push(currentChunk.trim());
      // Keep overlap
      const words = currentChunk.split(' ');
      currentChunk = words.slice(-overlap/10).join(' ') + ' ' + sentence;
    } else {
      currentChunk += sentence + '. ';
    }
  }
  
  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }
  
  return chunks;
}

// Generate embeddings
async function getEmbeddings(texts) {
  try {
    const response = await openai.embeddings.create({
      model: EMBEDDING_MODEL,
      input: texts,
    });
    return response.data.map(d => d.embedding);
  } catch (error) {
    console.error('Error generating embeddings:', error);
    throw error;
  }
}

// Initialize collection
async function initializeCollection() {
  try {
    // Delete if exists
    try {
      await qdrant.deleteCollection(COLLECTION_NAME);
      console.log('Deleted existing collection');
    } catch (e) {
      // Collection doesn't exist, that's fine
    }
    
    // Create new collection
    await qdrant.createCollection(COLLECTION_NAME, {
      vectors: {
        size: EMBEDDING_DIMENSION,
        distance: 'Cosine',
      },
    });
    
    console.log('Created new collection:', COLLECTION_NAME);
    return true;
  } catch (error) {
    console.error('Error initializing collection:', error);
    return false;
  }
}

// Process PDFs
async function processPDFs() {
  const pdfDirs = [
    { path: '../../docs/data/SOP/', type: 'Industry Standards & Regulations', category: 'SOP' },
    { path: '../../docs/data/ North Carolina Building & Inspection Codes /', type: 'NC Building Codes', category: 'Building Codes' }
  ];
  
  let allDocuments = [];
  let pointId = 0;
  
  for (const dir of pdfDirs) {
    const fullPath = path.resolve(__dirname, dir.path);
    
    if (!fs.existsSync(fullPath)) {
      console.log(`Directory not found: ${fullPath}`);
      continue;
    }
    
    const files = fs.readdirSync(fullPath).filter(f => f.endsWith('.pdf'));
    console.log(`Found ${files.length} PDFs in ${dir.path}`);
    
    for (const file of files) {
      const filePath = path.join(fullPath, file);
      console.log(`Processing: ${file}`);
      
      try {
        const dataBuffer = fs.readFileSync(filePath);
        const data = await pdf(dataBuffer);
        
        // Clean text
        const text = data.text.replace(/\s+/g, ' ').trim();
        
        // Chunk text
        const chunks = chunkText(text);
        console.log(`  Split into ${chunks.length} chunks`);
        
        // Process chunks in batches
        const batchSize = 10;
        for (let i = 0; i < chunks.length; i += batchSize) {
          const batch = chunks.slice(i, i + batchSize);
          const embeddings = await getEmbeddings(batch);
          
          // Determine specific category based on filename
          const getSpecificCategory = (filename) => {
            if (filename.toLowerCase().includes('internachi')) return 'Industry Standards';
            if (filename.toLowerCase().includes('nchilb')) return 'State Regulations';
            if (filename.toLowerCase().includes('building')) return 'Building Codes';
            return dir.category; // fallback
          };

          // Create points
          const points = batch.map((chunk, idx) => ({
            id: pointId++,
            vector: embeddings[idx],
            payload: {
              content: chunk,
              source: file.replace('.pdf', ''),
              document_type: dir.type,
              category: getSpecificCategory(file),
              chunk_index: i + idx,
              total_chunks: chunks.length,
            },
          }));
          
          // Upload to Qdrant
          await qdrant.upsert(COLLECTION_NAME, {
            wait: true,
            points: points,
          });
          
          console.log(`  Uploaded batch ${Math.floor(i/batchSize) + 1}`);
        }
        
      } catch (error) {
        console.error(`Error processing ${file}:`, error.message);
      }
    }
  }
  
  console.log(`\n✅ Processed ${pointId} total chunks`);
  return pointId;
}

// Main function
async function main() {
  console.log('🚀 Starting PDF ingestion...\n');
  
  // Check environment variables
  if (!process.env.OPENAI_API_KEY) {
    console.error('❌ OPENAI_API_KEY not found in environment');
    return;
  }
  
  if (!process.env.QDRANT_URL || !process.env.QDRANT_API_KEY) {
    console.error('❌ Qdrant credentials not found in environment');
    return;
  }
  
  try {
    // Initialize collection
    console.log('1. Initializing Qdrant collection...');
    const initialized = await initializeCollection();
    if (!initialized) {
      console.error('❌ Failed to initialize collection');
      return;
    }
    
    // Process PDFs
    console.log('\n2. Processing PDFs...');
    const totalChunks = await processPDFs();
    
    console.log(`\n🎉 SUCCESS! Ingested ${totalChunks} chunks into Qdrant`);
    console.log('Ready to test your RAG application!');
    
  } catch (error) {
    console.error('❌ Fatal error:', error);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { main };