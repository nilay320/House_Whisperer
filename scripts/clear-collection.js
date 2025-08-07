const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';

async function clearCollection() {
  try {
    console.log('🗑️  Clearing collection:', COLLECTION_NAME);
    
    // Check if collection exists
    try {
      const info = await qdrant.getCollection(COLLECTION_NAME);
      console.log(`📊 Current collection has ${info.points_count} points`);
      
      // Delete the collection
      await qdrant.deleteCollection(COLLECTION_NAME);
      console.log('✅ Collection deleted successfully');
      
    } catch (error) {
      if (error.message.includes('Not found')) {
        console.log('ℹ️  Collection does not exist');
      } else {
        throw error;
      }
    }
    
    // Create a fresh collection
    console.log('🆕 Creating fresh collection...');
    await qdrant.createCollection(COLLECTION_NAME, {
      vectors: {
        size: 1536,
        distance: 'Cosine'
      }
    });
    
    console.log('✅ Fresh collection created successfully');
    
  } catch (error) {
    console.error('❌ Error clearing collection:', error.message);
  }
}

clearCollection();