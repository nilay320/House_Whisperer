const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');
const { OpenAI } = require('openai');
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

// Simple iterative chunking (no recursion)
function simpleChunkText(text, chunkSize = 1000, chunkOverlap = 200) {
  const chunks = [];
  let start = 0;
  
  while (start < text.length) {
    let end = start + chunkSize;
    
    // If this isn't the last chunk, try to break at a good point
    if (end < text.length) {
      // Look for paragraph break
      let breakPoint = text.lastIndexOf('\n\n', end);
      if (breakPoint > start + 500) {
        end = breakPoint;
      } else {
        // Look for sentence break
        breakPoint = text.lastIndexOf('. ', end);
        if (breakPoint > start + 500) {
          end = breakPoint + 1;
        }
      }
    }
    
    const chunk = text.slice(start, end).trim();
    if (chunk.length > 0) {
      chunks.push(chunk);
    }
    
    // Next chunk starts with overlap
    start = Math.max(start + 1, end - chunkOverlap);
  }
  
  console.log(`  ✅ Created ${chunks.length} chunks with simple method`);
  return chunks;
}

async function getEmbeddings(texts) {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: texts,
  });
  return response.data.map(d => d.embedding);
}

async function simpleNCIngestion() {
  try {
    console.log('🔄 Starting simple NC Building Codes ingestion...\n');
    
    // Get current collection info
    const info = await qdrant.getCollection(COLLECTION_NAME);
    const startPointId = info.points_count;
    console.log(`📊 Collection currently has ${info.points_count} points`);
    console.log(`📍 Starting from point ID: ${startPointId}`);
    
    // Load PDF
    const filePath = path.join(__dirname, '../../docs/data/ North Carolina Building & Inspection Codes /2024_nc_collection.pdf');
    console.log(`\n📄 Processing: ${path.basename(filePath)}`);
    
    const dataBuffer = fs.readFileSync(filePath);
    console.log(`  File size: ${(dataBuffer.length / 1024 / 1024).toFixed(1)}MB`);
    
    console.log(`⏳ Extracting text from PDF...`);
    const data = await pdf(dataBuffer);
    console.log(`  ✅ Extracted ${data.numpages} pages`);
    
    const text = data.text.replace(/\s+/g, ' ').trim();
    console.log(`  Text length: ${text.length} characters`);
    
    console.log(`⏳ Chunking text with simple method...`);
    const chunks = simpleChunkText(text);
    
    console.log(`\n🎯 Processing ${chunks.length} chunks in batches of 10`);
    
    const batchSize = 10;
    let pointId = startPointId;
    let successfulBatches = 0;
    
    for (let i = 0; i < chunks.length; i += batchSize) {
      const batch = chunks.slice(i, i + batchSize);
      const currentBatch = Math.floor(i / batchSize) + 1;
      const totalBatches = Math.ceil(chunks.length / batchSize);
      
      console.log(`\n📦 Batch ${currentBatch}/${totalBatches} (${batch.length} chunks)`);
      
      try {
        // Generate embeddings
        console.log(`  🔄 Generating embeddings...`);
        const embeddings = await getEmbeddings(batch);
        
        // Create points
        const points = batch.map((chunk, idx) => ({
          id: pointId + idx,
          vector: embeddings[idx],
          payload: {
            content: chunk,
            source: "NC Building Codes 2024",
            document_name: "NC Building Codes",
            document_type: "NC Building Codes",
            category: "Building Codes",
            chunk_index: i + idx,
            total_chunks: chunks.length,
            file_name: "2024_nc_collection.pdf",
          },
        }));
        
        // Upload batch
        console.log(`  ⬆️  Uploading batch...`);
        await qdrant.upsert(COLLECTION_NAME, {
          wait: true,
          points: points,
        });
        
        pointId += batch.length;
        successfulBatches++;
        
        console.log(`  ✅ Batch ${currentBatch} completed successfully`);
        
        // Show progress
        const progress = ((i + batch.length) / chunks.length * 100).toFixed(1);
        console.log(`  📊 Progress: ${progress}% (${i + batch.length}/${chunks.length} chunks)`);
        
        // Rate limiting - small delay
        await new Promise(resolve => setTimeout(resolve, 200));
        
      } catch (error) {
        console.error(`❌ Batch ${currentBatch} failed:`, error.message);
        
        // Wait a bit and continue
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    
    // Final status
    const finalInfo = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`\n🎉 Ingestion completed!`);
    console.log(`📊 Final collection size: ${finalInfo.points_count} points`);
    console.log(`✅ Successfully processed ${successfulBatches}/${Math.ceil(chunks.length / batchSize)} batches`);
    console.log(`📈 Added ${finalInfo.points_count - info.points_count} new chunks`);
    
  } catch (error) {
    console.error('❌ Fatal error during ingestion:', error);
  }
}

simpleNCIngestion();