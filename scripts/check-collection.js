const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';

async function checkCollection() {
  try {
    console.log('🔍 Checking Qdrant collection:', COLLECTION_NAME);
    
    // Check if collection exists
    const collections = await qdrant.getCollections();
    console.log('\n📊 Available collections:');
    collections.collections.forEach(col => {
      console.log(`  - ${col.name} (${col.vectors_count} vectors)`);
    });
    
    // Get collection info
    const info = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`\n📈 Collection "${COLLECTION_NAME}" details:`);
    console.log(`  - Points count: ${info.points_count}`);
    console.log(`  - Vector size: ${info.config.params.vectors.size}`);
    
    // Get some sample points to see what data we have
    console.log('\n📋 Sample points:');
    const points = await qdrant.scroll(COLLECTION_NAME, {
      limit: 5,
      with_payload: true,
      with_vector: false
    });
    
    points.points.forEach((point, i) => {
      console.log(`\n  Point ${i + 1}:`);
      console.log(`    ID: ${point.id}`);
      console.log(`    Source: ${point.payload?.source || 'Unknown'}`);
      console.log(`    Document: ${point.payload?.document || 'Unknown'}`);
      console.log(`    Content preview: ${(point.payload?.content || '').substring(0, 200)}...`);
    });
    
  } catch (error) {
    console.error('❌ Error checking collection:', error.message);
  }
}

checkCollection();