const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

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
const PROGRESS_FILE = path.join(__dirname, 'nc-ingestion-progress.json');

// Chunking function
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

// Save progress
function saveProgress(data) {
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(data, null, 2));
}

// Load progress
function loadProgress() {
  try {
    if (fs.existsSync(PROGRESS_FILE)) {
      return JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8'));
    }
  } catch (error) {
    console.log('⚠️  Could not load progress file, starting fresh');
  }
  return null;
}

// Generate embeddings with retry
async function getEmbeddingsWithRetry(texts, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await openai.embeddings.create({
        model: EMBEDDING_MODEL,
        input: texts,
      });
      return response.data.map(d => d.embedding);
    } catch (error) {
      console.error(`❌ Embedding attempt ${attempt}/${maxRetries} failed:`, error.message);
      
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Exponential backoff
      const delay = Math.pow(2, attempt) * 1000;
      console.log(`⏳ Waiting ${delay}ms before retry...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Upload batch with retry
async function uploadBatchWithRetry(points, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      await qdrant.upsert(COLLECTION_NAME, {
        wait: true,
        points: points,
      });
      return true;
    } catch (error) {
      console.error(`❌ Upload attempt ${attempt}/${maxRetries} failed:`, error.message);
      
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Exponential backoff
      const delay = Math.pow(2, attempt) * 1000;
      console.log(`⏳ Waiting ${delay}ms before retry...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Prompt for user intervention
function promptUser(message) {
  console.log(`\n🚨 ${message}`);
  console.log(`\nOptions:`);
  console.log(`  1. Press Enter to continue`);
  console.log(`  2. Type 'skip' to skip this batch`);
  console.log(`  3. Type 'abort' to stop completely`);
  
  return new Promise((resolve) => {
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    
    process.stdin.once('data', (input) => {
      const choice = input.trim().toLowerCase();
      process.stdin.pause();
      
      if (choice === 'skip') {
        resolve('skip');
      } else if (choice === 'abort') {
        resolve('abort');
      } else {
        resolve('continue');
      }
    });
  });
}

async function resilientNCIngestion() {
  try {
    console.log('🔄 Starting resilient NC Building Codes ingestion...\n');
    
    // Load progress if exists
    let progress = loadProgress();
    let startBatch = 0;
    let startChunk = 0;
    let nextPointId = null;
    
    if (progress) {
      console.log(`📋 Found previous progress:`);
      console.log(`  - Last completed batch: ${progress.lastCompletedBatch}`);
      console.log(`  - Last completed chunk: ${progress.lastCompletedChunk}`);
      console.log(`  - Next point ID: ${progress.nextPointId}`);
      
      const userChoice = await promptUser(`Resume from batch ${progress.lastCompletedBatch + 1}?`);
      if (userChoice === 'abort') {
        console.log('🛑 Aborted by user');
        return;
      }
      
      if (userChoice === 'continue') {
        startBatch = progress.lastCompletedBatch + 1;
        startChunk = progress.lastCompletedChunk + 1;
        nextPointId = progress.nextPointId;
      }
    }
    
    // Get current collection info
    const info = await qdrant.getCollection(COLLECTION_NAME);
    if (!nextPointId) {
      nextPointId = info.points_count;
    }
    console.log(`📊 Collection currently has ${info.points_count} points`);
    console.log(`📍 Starting from point ID: ${nextPointId}`);
    
    // Load and process PDF
    const filePath = path.join(__dirname, '../../docs/data/ North Carolina Building & Inspection Codes /2024_nc_collection.pdf');
    console.log(`\n📄 Processing: ${path.basename(filePath)}`);
    
    const dataBuffer = fs.readFileSync(filePath);
    console.log(`  File size: ${(dataBuffer.length / 1024 / 1024).toFixed(1)}MB`);
    
    console.log(`⏳ Extracting text from PDF... (this may take a while)`);
    const data = await pdf(dataBuffer);
    console.log(`  ✅ Extracted ${data.numpages} pages`);
    
    const text = data.text.replace(/\s+/g, ' ').trim();
    console.log(`  Text length: ${text.length} characters`);
    
    console.log(`⏳ Chunking text...`);
    const chunks = chunkText(text);
    console.log(`  ✅ Split into ${chunks.length} chunks`);
    
    // Start from where we left off
    const remainingChunks = chunks.slice(startChunk);
    console.log(`\n🎯 Processing ${remainingChunks.length} remaining chunks`);
    console.log(`📊 Starting from batch ${startBatch + 1}/${Math.ceil(chunks.length / 10)}`);
    
    const batchSize = 10;
    let pointId = nextPointId;
    let successfulBatches = startBatch;
    let consecutiveFailures = 0;
    const maxConsecutiveFailures = 5;
    
    for (let i = 0; i < remainingChunks.length; i += batchSize) {
      const batch = remainingChunks.slice(i, i + batchSize);
      const currentBatch = startBatch + Math.floor(i / batchSize);
      const totalBatches = Math.ceil(chunks.length / batchSize);
      
      console.log(`\n📦 Batch ${currentBatch + 1}/${totalBatches} (${batch.length} chunks)`);
      
      try {
        // Generate embeddings
        console.log(`  🔄 Generating embeddings...`);
        const embeddings = await getEmbeddingsWithRetry(batch);
        
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
            chunk_index: startChunk + i + idx,
            total_chunks: chunks.length,
            file_name: "2024_nc_collection.pdf",
          },
        }));
        
        // Upload batch
        console.log(`  ⬆️  Uploading batch...`);
        await uploadBatchWithRetry(points);
        
        pointId += batch.length;
        successfulBatches = currentBatch + 1;
        consecutiveFailures = 0;
        
        // Save progress
        saveProgress({
          lastCompletedBatch: currentBatch,
          lastCompletedChunk: startChunk + i + batch.length - 1,
          nextPointId: pointId,
          totalChunks: chunks.length,
          successfulBatches: successfulBatches
        });
        
        console.log(`  ✅ Batch ${currentBatch + 1} completed successfully`);
        
        // Rate limiting
        await new Promise(resolve => setTimeout(resolve, 500));
        
      } catch (error) {
        consecutiveFailures++;
        console.error(`❌ Batch ${currentBatch + 1} failed:`, error.message);
        
        if (consecutiveFailures >= maxConsecutiveFailures) {
          const userChoice = await promptUser(`${consecutiveFailures} consecutive failures. What would you like to do?`);
          
          if (userChoice === 'abort') {
            console.log('🛑 Ingestion aborted by user');
            break;
          } else if (userChoice === 'skip') {
            console.log('⏭️  Skipping this batch');
            pointId += batch.length; // Skip the point IDs
            consecutiveFailures = 0;
            continue;
          }
          // 'continue' resets the failure count and tries again
          consecutiveFailures = 0;
        }
        
        // Wait before next attempt
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
    
    // Final status
    const finalInfo = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`\n🎉 Ingestion completed!`);
    console.log(`📊 Final collection size: ${finalInfo.points_count} points`);
    console.log(`✅ Successfully processed ${successfulBatches} batches`);
    
    // Cleanup progress file
    if (fs.existsSync(PROGRESS_FILE)) {
      fs.unlinkSync(PROGRESS_FILE);
      console.log(`🧹 Cleaned up progress file`);
    }
    
  } catch (error) {
    console.error('❌ Fatal error during ingestion:', error);
    console.log(`💾 Progress saved. You can resume with: node scripts/resilient-nc-ingestion.js`);
  }
}

// Handle process termination gracefully
process.on('SIGINT', () => {
  console.log('\n🛑 Ingestion interrupted by user');
  console.log('💾 Progress has been saved');
  console.log('🔄 Resume with: node scripts/resilient-nc-ingestion.js');
  process.exit(0);
});

resilientNCIngestion();