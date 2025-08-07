#!/usr/bin/env python3
"""Simple test of the Python chat API components."""

import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

def test_complete_pipeline():
    """Test the complete RAG pipeline."""
    print("🐍 Testing Complete Python RAG Pipeline\n")
    
    try:
        from chat import get_embedding, retrieve, generate_stream
        
        # Test query
        query = "What are the requirements for electrical inspections in North Carolina?"
        print(f"🔍 Query: {query}\n")
        
        # Step 1: Generate embedding
        print("1️⃣ Generating query embedding...")
        embedding = get_embedding(query)
        print(f"   ✅ Generated embedding: {len(embedding)} dimensions")
        
        # Step 2: Retrieve context
        print("\n2️⃣ Retrieving relevant context...")
        context = retrieve(query, limit=3)
        print(f"   ✅ Retrieved {len(context)} chunks")
        
        for i, chunk in enumerate(context):
            print(f"   [{i+1}] Score: {chunk['score']:.4f}")
            print(f"       Source: {chunk['source']}")
            print(f"       Content: {chunk['content'][:100]}...")
            print()
        
        # Step 3: Generate response
        print("3️⃣ Generating streaming response...")
        stream_gen = generate_stream(query, context)
        
        content_parts = []
        sources_received = None
        chunk_count = 0
        
        for chunk in stream_gen:
            chunk_count += 1
            if chunk.startswith('data: '):
                data_str = chunk[6:].strip()
                try:
                    data = json.loads(data_str)
                    if 'content' in data:
                        content_parts.append(data['content'])
                    elif 'sources' in data:
                        sources_received = data['sources']
                        print(f"   📚 Received sources: {len(sources_received)} items")
                        break
                except json.JSONDecodeError:
                    continue
        
        full_response = ''.join(content_parts)
        print(f"   ✅ Generated response: {len(full_response)} characters")
        print(f"   📊 Stream chunks: {chunk_count}")
        
        # Display results
        print(f"\n{'='*60}")
        print("FINAL RESULTS")
        print(f"{'='*60}")
        
        print(f"\n💭 Generated Response:")
        print(f"{full_response}")
        
        print(f"\n📚 Sources Used:")
        for i, source in enumerate(sources_received, 1):
            print(f"   {i}. {source['source']} (score: {source['score']:.4f})")
        
        print(f"\n🎉 Complete pipeline test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    if success:
        print("\n✅ Python API is ready for deployment!")
    else:
        print("\n❌ Python API needs fixes before deployment")