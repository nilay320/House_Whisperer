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

// Get command line arguments
const args = process.argv.slice(2);
const targetDocument = args[0]; // e.g., "InterNACHI SOP" or "NCHILB" or "all"

// Improved chunking function (inspired by RecursiveCharacterTextSplitter)
function chunkText(text, chunkSize = 1000, chunkOverlap = 200) {
  const chunks = [];
  const separators = ['\n\n', '\n', '. ', '.', '!', '?', ';', ':', ' '];
  
  function splitBySeparator(text, separator) {
    return text.split(separator).filter(s => s.trim().length > 0);
  }
  
  function createChunks(textParts, separator) {
    const result = [];
    let currentChunk = '';
    
    for (const part of textParts) {
      const pieceWithSep = currentChunk ? currentChunk + separator + part : part;
      
      if (pieceWithSep.length <= chunkSize) {
        currentChunk = pieceWithSep;
      } else {
        if (currentChunk) {
          result.push(currentChunk.trim());
          // Add overlap
          const words = currentChunk.split(' ');
          const overlapWords = Math.floor(chunkOverlap / 5); // ~40 words for 200 chars
          currentChunk = words.slice(-overlapWords).join(' ') + separator + part;
        } else {
          currentChunk = part;
        }
      }
    }
    
    if (currentChunk.trim()) {
      result.push(currentChunk.trim());
    }
    
    return result;
  }
  
  // Try each separator in order
  let parts = [text];
  
  for (const separator of separators) {
    const newParts = [];
    
    for (const part of parts) {
      if (part.length <= chunkSize) {
        newParts.push(part);
      } else {
        const splitParts = splitBySeparator(part, separator);
        const chunkedParts = createChunks(splitParts, separator);
        newParts.push(...chunkedParts);
      }
    }
    
    parts = newParts;
    
    // If all parts are small enough, we're done
    if (parts.every(p => p.length <= chunkSize)) {
      break;
    }
  }
  
  return parts.filter(chunk => chunk.trim().length > 0);
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

// Initialize collection (only if it doesn't exist)
async function ensureCollection() {
  try {
    const collections = await qdrant.getCollections();
    const exists = collections.collections.some(c => c.name === COLLECTION_NAME);
    
    if (!exists) {
      await qdrant.createCollection(COLLECTION_NAME, {
        vectors: {
          size: EMBEDDING_DIMENSION,
          distance: 'Cosine',
        },
      });
      console.log('✅ Created new collection:', COLLECTION_NAME);
    } else {
      console.log('✅ Collection already exists:', COLLECTION_NAME);
    }
    
    return true;
  } catch (error) {
    console.error('Error with collection:', error);
    return false;
  }
}

// Delete existing chunks for a specific document
async function deleteDocumentChunks(documentName) {
  try {
    console.log(`🔍 Looking for existing chunks for: "${documentName}"`);
    
    // First, let's test a simple scroll without filter to see if API works
    console.log(`🧪 Testing basic scroll first...`);
    const testScroll = await qdrant.scroll(COLLECTION_NAME, {
      limit: 5,
      with_payload: true
    });
    
    console.log(`✅ Basic scroll works. Found ${testScroll.points.length} points`);
    if (testScroll.points.length > 0) {
      console.log(`📋 Sample sources in collection:`);
      testScroll.points.forEach((point, i) => {
        console.log(`   ${i+1}. "${point.payload.source}"`);
      });
    }
    
    // Now try with filter - use exact match format from working scripts
    console.log(`🔍 Now searching for exact source: "${documentName}"`);
    
    let allPoints = [];
    let offset = null;
    
    do {
      const scrollResult = await qdrant.scroll(COLLECTION_NAME, {
        filter: {
          must: [
            {
              match: {
                key: "source",
                value: documentName
              }
            }
          ]
        },
        limit: 100,
        offset: offset,
        with_payload: false,
        with_vector: false
      });
      
      if (scrollResult.points) {
        allPoints.push(...scrollResult.points.map(p => p.id));
        offset = scrollResult.next_page_offset;
      } else {
        break;
      }
    } while (offset);
    
    if (allPoints.length > 0) {
      console.log(`🗑️  Found ${allPoints.length} chunks to delete for: "${documentName}"`);
      
      // Delete in batches of 100
      const batchSize = 100;
      for (let i = 0; i < allPoints.length; i += batchSize) {
        const batch = allPoints.slice(i, i + batchSize);
        
        await qdrant.delete(COLLECTION_NAME, {
          points: batch
        });
      }
      
      console.log(`✅ Deleted ${allPoints.length} existing chunks for: "${documentName}"`);
    } else {
      console.log(`ℹ️  No existing chunks found for: "${documentName}"`);
    }
    
    return true;
  } catch (error) {
    console.error(`❌ Error in cleanup for "${documentName}":`, error.data?.status?.error || error.message);
    // Don't fail the whole process for cleanup errors
    return true;
  }
}

// Get next available point ID
async function getNextPointId() {
  try {
    const info = await qdrant.getCollection(COLLECTION_NAME);
    return info.points_count || 0;
  } catch (error) {
    return 0;
  }
}

// Process a single PDF file
async function processSinglePDF(filePath, dirType, startingId) {
  const file = path.basename(filePath);
  console.log(`\n📄 Processing: ${file}`);
  
  try {
    const dataBuffer = fs.readFileSync(filePath);
    console.log(`  File size: ${(dataBuffer.length / 1024 / 1024).toFixed(1)}MB`);
    
    const data = await pdf(dataBuffer);
    console.log(`  Extracted ${data.numpages} pages`);
    
    const text = data.text.replace(/\s+/g, ' ').trim();
    console.log(`  Text length: ${text.length} characters`);
    
    const chunks = chunkText(text);
    console.log(`  Split into ${chunks.length} chunks`);
    
    // Determine category and source name
    const getSourceInfo = (filename) => {
      const name = filename.replace('.pdf', '');
      if (filename.toLowerCase().includes('internachi')) {
        return {
          category: 'Industry Standards',
          source: 'InterNACHI Standards of Practice',
          displayName: 'InterNACHI SOP'
        };
      }
      if (filename.toLowerCase().includes('nchilb')) {
        return {
          category: 'State Regulations', 
          source: 'NC Home Inspector Licensure Board',
          displayName: 'NCHILB Standards'
        };
      }
      if (filename.toLowerCase().includes('2024_nc_collection')) {
        return {
          category: 'Building Codes',
          source: 'NC Building Codes 2024',
          displayName: 'NC Building Codes'
        };
      }
      return {
        category: 'Other',
        source: name,
        displayName: name
      };
    };
    
    const sourceInfo = getSourceInfo(file);
    
    // Delete existing chunks for this document (disabled due to API filter issues)
    console.log(`ℹ️  Skipping cleanup for: ${sourceInfo.source} (filter API broken)`);
    // await deleteDocumentChunks(sourceInfo.source);
    
    let pointId = startingId;
    const batchSize = 10;
    
    for (let i = 0; i < chunks.length; i += batchSize) {
      const batch = chunks.slice(i, i + batchSize);
      console.log(`  Batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(chunks.length/batchSize)}...`);
      
      const embeddings = await getEmbeddings(batch);
      
      const points = batch.map((chunk, idx) => ({
        id: pointId++,
        vector: embeddings[idx],
        payload: {
          content: chunk,
          source: sourceInfo.source,
          document_name: sourceInfo.displayName,
          document_type: dirType,
          category: sourceInfo.category,
          chunk_index: i + idx,
          total_chunks: chunks.length,
          file_name: file,
        },
      }));
      
      await qdrant.upsert(COLLECTION_NAME, {
        wait: true,
        points: points,
      });
      
      console.log(`  ✅ Uploaded batch ${Math.floor(i/batchSize) + 1}`);
    }
    
    console.log(`✅ Completed ${file}: ${chunks.length} chunks processed`);
    return chunks.length;
    
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
    return 0;
  }
}

// Main function
async function main() {
  console.log('🔄 Document-specific PDF ingestion\n');
  
  if (!targetDocument) {
    console.log('Usage:');
    console.log('  npm run ingest:doc "InterNACHI SOP"');
    console.log('  npm run ingest:doc "NCHILB"');
    console.log('  npm run ingest:doc "2024_nc_collection"');
    console.log('  npm run ingest:doc "all"');
    return;
  }
  
  console.log(`🎯 Target: ${targetDocument}\n`);
  
  try {
    // Ensure collection exists
    const ready = await ensureCollection();
    if (!ready) return;
    
    let totalChunks = 0;
    const startId = await getNextPointId();
    
    // Define all available documents
    const documents = [
      { path: '../../docs/data/SOP/InterNACHI SOP.pdf', type: 'Industry Standards & Regulations' },
      { path: '../../docs/data/SOP/NCHILB NORTH CAROLINA HOME INSPECTOR LICENSURE BOARD.pdf', type: 'Industry Standards & Regulations' },
      { path: '../../docs/data/ North Carolina Building & Inspection Codes /2024_nc_collection.pdf', type: 'NC Building Codes' }
    ];
    
    // Filter documents based on target
    let docsToProcess = [];
    
    if (targetDocument === 'all') {
      docsToProcess = documents;
    } else {
      docsToProcess = documents.filter(doc => 
        path.basename(doc.path).toLowerCase().includes(targetDocument.toLowerCase())
      );
    }
    
    if (docsToProcess.length === 0) {
      console.error(`❌ No documents found matching: ${targetDocument}`);
      return;
    }
    
    console.log(`📚 Processing ${docsToProcess.length} document(s)...\n`);
    
    // Process each document
    for (const doc of docsToProcess) {
      const fullPath = path.resolve(__dirname, doc.path);
      
      if (!fs.existsSync(fullPath)) {
        console.log(`❌ File not found: ${fullPath}`);
        continue;
      }
      
      const chunks = await processSinglePDF(fullPath, doc.type, startId + totalChunks);
      totalChunks += chunks;
    }
    
    console.log(`\n🎉 SUCCESS! Processed ${totalChunks} chunks total`);
    
  } catch (error) {
    console.error('❌ Fatal error:', error);
  }
}

if (require.main === module) {
  main();
}