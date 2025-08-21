const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../frontend/.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';

async function deleteNCBuildingCodes() {
  try {
    console.log('🗑️  Deleting ONLY NC Building Codes (keeping InterNACHI + NCHILB)...\n');
    
    // Get current status
    const info = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`📊 Current collection has ${info.points_count} points`);
    
    // Count points by source
    const sources = ['InterNACHI Standards of Practice', 'NC Home Inspector Licensure Board', 'NC Building Codes 2024'];
    for (const source of sources) {
      const result = await qdrant.scroll(COLLECTION_NAME, {
        filter: {
          must: [{ 
            match: { 
              key: "source", 
              value: source 
            } 
          }]
        },
        limit: 1,
        with_payload: false,
        with_vector: false
      });
      
      // Get total count by scrolling through all
      let count = 0;
      let offset = null;
      do {
        const scrollResult = await qdrant.scroll(COLLECTION_NAME, {
          filter: { 
            must: [{ 
              match: { 
                key: "source", 
                value: source 
              } 
            }] 
          },
          limit: 100,
          offset: offset,
          with_payload: false,
          with_vector: false
        });
        count += scrollResult.points.length;
        offset = scrollResult.next_page_offset;
      } while (offset);
      
      console.log(`📋 ${source}: ${count} chunks`);
    }
    
    // Delete NC Building Codes chunks by IDs
    console.log('\n🗑️  Deleting NC Building Codes chunks...');
    
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
      
      console.log(`📋 Found ${allNCPoints.length} NC Building Codes points so far...`);
      
    } while (offset);
    
    console.log(`\n📊 Total NC Building Codes chunks to delete: ${allNCPoints.length}`);
    
    if (allNCPoints.length > 0) {
      // Delete in batches of 100
      const batchSize = 100;
      for (let i = 0; i < allNCPoints.length; i += batchSize) {
        const batch = allNCPoints.slice(i, i + batchSize);
        
        try {
          await qdrant.delete(COLLECTION_NAME, {
            points: batch
          });
          
          console.log(`✅ Deleted batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(allNCPoints.length/batchSize)} (${batch.length} points)`);
          
        } catch (error) {
          console.error(`❌ Error deleting batch ${Math.floor(i/batchSize) + 1}:`, error.message);
        }
      }
    } else {
      console.log('ℹ️  No NC Building Codes chunks found to delete');
    }
    
    // Final verification
    const finalInfo = await qdrant.getCollection(COLLECTION_NAME);
    console.log(`\n📈 Final collection size: ${finalInfo.points_count} points`);
    
    // Verify what's left
    console.log('\n📋 Remaining sources:');
    for (const source of ['InterNACHI Standards of Practice', 'NC Home Inspector Licensure Board', 'NC Building Codes 2024']) {
      let count = 0;
      let offset = null;
      do {
        const scrollResult = await qdrant.scroll(COLLECTION_NAME, {
          filter: { 
            must: [{ 
              match: { 
                key: "source", 
                value: source 
              } 
            }] 
          },
          limit: 100,
          offset: offset,
          with_payload: false,
          with_vector: false
        });
        count += scrollResult.points.length;
        offset = scrollResult.next_page_offset;
      } while (offset);
      
      console.log(`  - ${source}: ${count} chunks`);
    }
    
    console.log(`\n✅ NC Building Codes deletion complete!`);
    console.log(`🔄 Ready for resilient re-ingestion with: node scripts/resilient-nc-ingestion.js`);
    
  } catch (error) {
    console.error('❌ Error during NC Building Codes deletion:', error);
  }
}

deleteNCBuildingCodes();