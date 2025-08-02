const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

const { QdrantClient } = require('@qdrant/js-client-rest');

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

const COLLECTION_NAME = 'inspector-standards';

async function checkSources() {
  try {
    console.log('🔍 Checking data sources in collection...');
    
    // Get all points to analyze sources
    let offset = null;
    const sources = new Set();
    const documents = new Set();
    let totalPoints = 0;
    
    do {
      const result = await qdrant.scroll(COLLECTION_NAME, {
        limit: 100,
        offset: offset,
        with_payload: true,
        with_vector: false
      });
      
      result.points.forEach(point => {
        if (point.payload?.source) {
          sources.add(point.payload.source);
        }
        if (point.payload?.document) {
          documents.add(point.payload.document);
        }
        totalPoints++;
      });
      
      offset = result.next_page_offset;
    } while (offset);
    
    console.log(`\n📊 Analysis of ${totalPoints} points:`);
    console.log('\n🏷️  Sources found:');
    sources.forEach(source => console.log(`  - ${source}`));
    
    console.log('\n📄 Documents found:');
    documents.forEach(doc => console.log(`  - ${doc}`));
    
    // Check specifically for NC data
    console.log('\n🔍 Looking for NC-specific content...');
    const searchResults = await qdrant.scroll(COLLECTION_NAME, {
      limit: 10,
      filter: {
        should: [
          {
            match: {
              key: "source",
              value: "2024_nc_collection"
            }
          }
        ]
      },
      with_payload: true,
      with_vector: false
    });
    
    if (searchResults.points.length > 0) {
      console.log(`Found ${searchResults.points.length} NC points:`);
      searchResults.points.forEach((point, i) => {
        console.log(`\n  NC Point ${i + 1}:`);
        console.log(`    Source: ${point.payload?.source}`);
        console.log(`    Content: ${(point.payload?.content || '').substring(0, 150)}...`);
      });
    } else {
      console.log('❌ No NC-specific data found with source "2024_nc_collection"');
    }
    
  } catch (error) {
    console.error('❌ Error checking sources:', error.message);
  }
}

checkSources();