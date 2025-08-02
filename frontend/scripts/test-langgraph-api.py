#!/usr/bin/env python3
"""Test the LangGraph-enabled API."""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

def test_langgraph_api():
    """Test the LangGraph API functions."""
    print("🧪 Testing LangGraph API\n")
    
    try:
        from chat import query_rag_system
        
        # Test query
        query = "What are the requirements for electrical inspections in North Carolina?"
        print(f"🔍 Query: {query}\n")
        
        # Test the LangGraph RAG system
        result = query_rag_system(query, thread_id="test_session")
        
        if result["success"]:
            print("✅ LangGraph RAG System Test Results:")
            print(f"📝 Response: {result['response']}")
            print(f"\n📚 Sources ({len(result['sources'])}):")
            for i, source in enumerate(result['sources'], 1):
                print(f"   {i}. {source['source']} (score: {source['score']:.4f})")
            
            print(f"\n🎉 LangGraph API test successful!")
            return True
        else:
            print(f"❌ LangGraph test failed: {result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_langgraph_api()
    if success:
        print("\n✅ LangGraph API is ready!")
    else:
        print("\n❌ LangGraph API needs fixes")