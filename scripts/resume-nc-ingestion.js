const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');
const { OpenAI } = require('openai');
const pdf = require('pdf-parse');
const fs = require('fs');

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

// Chunking function (same as before)
function chunkText(text, chunkSize = 1000, chunkOverlap = 200) {
  const chunks = [];
  const separators = ['\n\n', '\n', '. ', '.', '!', '?', ';', ':', ' '];
  
  let parts = [text];
  
  for (const separator of separators) {
    const newParts = [];
    for (const part of parts) {
      if (part.length <= chunkSize) {
        newParts.push(part);
      } else {
        const split = part.split(separator);
        for (let i = 0; i < split.length; i++) {
          let chunk = split[i];
          if (i > 0) chunk = separator + chunk;
          
          if (chunk.length > chunkSize && separator !== ' ') {
            // Further split this chunk
            const subChunks = chunkText(chunk, chunkSize, chunkOverlap);
            newParts.push(...subChunks);
          } else {
            newParts.push(chunk);
          }
        }
      }
    }
    parts = newParts;
    
    if (parts.every(p => p.length <= chunkSize)) {
      break;
    }
  }
  
  return parts.filter(chunk => chunk.trim().length > 0);
}

async function getEmbeddings(texts) {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: texts,
  });
  return response.data.map(d => d.embedding);
}

async function resumeNCIngestion() {
  try {
    console.log('🔄 Resuming NC Building Codes ingestion...\n');
    
    // Check current collection status
    const info = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`📊 Current collection has ${info.points_count} points`);
    
    // Count existing NC Building Codes chunks
    const ncPoints = await qdrant.scroll(COLLECTION_NAME, {
      filter: {
        must: [
          {
            match: {
              key: "source",
              value: "NC Building Codes 2024"
            }
          }
        ]
      },
      limit: 1,
      with_payload: true,
      with_vector: false
    });
    
    console.log(`📋 Found existing NC Building Codes chunks. Resuming will continue from where we left off.`);
    
    // Load and process the PDF
    const filePath = path.join(__dirname, '../../docs/data/ North Carolina Building & Inspection Codes /2024_nc_collection.pdf');
    console.log(`📄 Processing: ${path.basename(filePath)}`);
    
    const dataBuffer = fs.readFileSync(filePath);
    console.log(`  File size: ${(dataBuffer.length / 1024 / 1024).toFixed(1)}MB`);
    
    const data = await pdf(dataBuffer);
    console.log(`  Extracted ${data.numpages} pages`);
    
    const text = data.text.replace(/\s+/g, ' ').trim();
    console.log(`  Text length: ${text.length} characters`);
    
    const chunks = chunkText(text);
    console.log(`  Split into ${chunks.length} chunks`);
    
    // Get the next available point ID
    const nextId = info.points_count;
    console.log(`  Starting from point ID: ${nextId}`);
    
    // Calculate which batch to start from (assuming 10 chunks per batch)
    const batchSize = 10;
    const existingNCChunks = Math.max(0, nextId - 362); // 47 InterNACHI + 315 NCHILB = 362
    const startBatch = Math.floor(existingNCChunks / batchSize);
    const startChunk = startBatch * batchSize;
    
    console.log(`  Resuming from batch ${startBatch + 1}, chunk ${startChunk + 1}`);
    console.log(`  Remaining chunks to process: ${chunks.length - startChunk}`);
    
    if (startChunk >= chunks.length) {
      console.log('✅ NC Building Codes already fully ingested!');
      return;
    }
    
    let pointId = nextId;
    const remainingChunks = chunks.slice(startChunk);
    
    for (let i = 0; i < remainingChunks.length; i += batchSize) {
      const batch = remainingChunks.slice(i, i + batchSize);
      const currentBatch = startBatch + Math.floor(i / batchSize) + 1;
      const totalBatches = Math.ceil(chunks.length / batchSize);
      
      console.log(`  Batch ${currentBatch}/${totalBatches}...`);
      
      try {
        const embeddings = await getEmbeddings(batch);
        
        const points = batch.map((chunk, idx) => ({
          id: pointId++,
          vector: embeddings[idx],
          payload: {
            content: chunk,
            source: "NC Building Codes 2024",
            document_name: "NC Building Codes",
            document_type: "NC Building Codes",
            category: "Building Codes",
            chunk_index: startChunk + i + idx,
            total_chunks: chunks.length,
            file_name: "2024_nc_collection.pdf",
          },
        }));
        
        await qdrant.upsert(COLLECTION_NAME, {
          wait: true,
          points: points,
        });
        
        console.log(`  ✅ Uploaded batch ${currentBatch}`);
        
        // Small delay to avoid rate limits
        await new Promise(resolve => setTimeout(resolve, 100));
        
      } catch (error) {
        console.error(`❌ Error in batch ${currentBatch}:`, error.message);
        console.log(`🔄 Continuing with next batch...`);
      }
    }
    
    console.log(`\n🎉 SUCCESS! NC Building Codes ingestion completed`);
    console.log(`📊 Total chunks processed: ${chunks.length}`);
    
    // Final collection status
    const finalInfo = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`📈 Final collection size: ${finalInfo.points_count} points`);
    
  } catch (error) {
    console.error('❌ Error resuming ingestion:', error);
  }
}

resumeNCIngestion();