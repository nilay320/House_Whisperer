const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });
const { QdrantClient } = require('@qdrant/js-client-rest');
const { OpenAI } = require('openai');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const qdrant = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

async function testRAGPipeline() {
  console.log('🧪 Testing RAG Pipeline...\n');
  
  try {
    console.log('1. Testing Qdrant connection...');
    const collections = await qdrant.getCollections();
    console.log('✅ Qdrant connected');
    
    console.log('2. Testing collection info...');
    const info = await qdrant.getCollection('inspector-standards');
    console.log(`✅ Collection has ${info.points_count} points`);
    
    console.log('3. Testing embedding generation...');
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: 'What is the required clearance for electrical panels?',
    });
    console.log('✅ OpenAI embeddings working');
    
    console.log('4. Testing vector search...');
    const searchResult = await qdrant.search('inspector-standards', {
      vector: response.data[0].embedding,
      limit: 3,
      with_payload: true,
    });
    
    console.log(`✅ Found ${searchResult.length} results:`);
    searchResult.forEach((result, i) => {
      console.log(`   ${i+1}. Score: ${result.score.toFixed(3)} | Source: ${result.payload.source}`);
      console.log(`      Content: ${result.payload.content.substring(0, 100)}...`);
    });
    
    console.log('\n🎉 RAG pipeline is working!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testRAGPipeline();