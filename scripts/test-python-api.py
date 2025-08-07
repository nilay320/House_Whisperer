#!/usr/bin/env python3
"""Test script for the Python chat API."""

import sys
import os
import json
import requests

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

# Set up environment variables for testing
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

def test_python_api_directly():
    """Test the Python API functions directly."""
    print("🧪 Testing Python API functions directly...\n")
    
    try:
        from chat import get_embedding, retrieve, generate_stream
        
        # Test embedding generation
        print("1. Testing embedding generation...")
        test_text = "What are the requirements for electrical inspections?"
        embedding = get_embedding(test_text)
        print(f"   ✅ Generated embedding with {len(embedding)} dimensions")
        
        # Test retrieval
        print("\n2. Testing vector retrieval...")
        context = retrieve(test_text)
        print(f"   ✅ Retrieved {len(context)} relevant chunks")
        for i, chunk in enumerate(context):
            print(f"   [{i+1}] Score: {chunk['score']:.4f}, Source: {chunk['source']}")
        
        # Test streaming (just first few chunks)
        print("\n3. Testing response generation...")
        stream_gen = generate_stream(test_text, context)
        chunk_count = 0
        for chunk in stream_gen:
            if chunk_count < 3:  # Only show first 3 chunks
                print(f"   Stream chunk: {chunk.strip()}")
            chunk_count += 1
            if chunk_count >= 10:  # Limit for testing
                break
        print(f"   ✅ Generated {chunk_count} stream chunks")
        
        print("\n🎉 All direct API tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Direct API test failed: {e}")
        return False

def test_api_as_module():
    """Test importing the API as a module."""
    print("🧪 Testing Python API module import...\n")
    
    try:
        # Test that we can import the handler
        from chat import handler
        print("   ✅ Successfully imported handler class")
        
        # Test that required environment variables are set
        required_vars = ['OPENAI_API_KEY', 'QDRANT_URL', 'QDRANT_API_KEY']
        for var in required_vars:
            if os.environ.get(var):
                print(f"   ✅ {var} is set")
            else:
                print(f"   ❌ {var} is missing")
                return False
                
        print("\n🎉 Module import test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Module import test failed: {e}")
        return False

if __name__ == "__main__":
    print("🐍 Testing Python Chat API\n")
    
    # Test module import first
    if not test_api_as_module():
        print("\n❌ Module tests failed, skipping function tests")
        sys.exit(1)
    
    print("\n" + "="*50 + "\n")
    
    # Test API functions
    if not test_python_api_directly():
        print("\n❌ Function tests failed")
        sys.exit(1)
    
    print("\n🎉 All Python API tests passed!")
    print("\n📝 Next steps:")
    print("   1. Deploy to Vercel: vercel --prod")
    print("   2. Test the deployed endpoint")
    print("   3. Update frontend if needed")