const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';

async function cleanRestartNC() {
  try {
    console.log('🧹 Cleaning NC Building Codes data for fresh restart...\n');
    
    // Get current status
    const info = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`📊 Current collection has ${info.points_count} points`);
    
    // Delete NC Building Codes chunks by scrolling and deleting by IDs
    console.log('🗑️  Finding NC Building Codes chunks to delete...');
    
    let allNCPoints = [];
    let offset = null;
    
    do {
      const result = await qdrant.scroll(COLLECTION_NAME, {
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
        limit: 100,
        offset: offset,
        with_payload: false,
        with_vector: false
      });
      
      allNCPoints.push(...result.points.map(p => p.id));
      offset = result.next_page_offset;
      
    } while (offset);
    
    console.log(`📋 Found ${allNCPoints.length} NC Building Codes chunks to delete`);
    
    if (allNCPoints.length > 0) {
      // Delete in batches
      const batchSize = 100;
      for (let i = 0; i < allNCPoints.length; i += batchSize) {
        const batch = allNCPoints.slice(i, i + batchSize);
        
        await qdrant.delete(COLLECTION_NAME, {
          points: batch
        });
        
        console.log(`🗑️  Deleted batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(allNCPoints.length/batchSize)}`);
      }
    }
    
    // Final status
    const finalInfo = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`\n✅ Cleanup complete! Collection now has ${finalInfo.points_count} points`);
    console.log(`🔄 Now you can run: npm run ingest:doc "2024_nc_collection"`);
    
  } catch (error) {
    console.error('❌ Error during cleanup:', error);
  }
}

cleanRestartNC();