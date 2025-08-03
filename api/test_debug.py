#!/usr/bin/env python3
"""Debug test for web search integration."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

# Test if Tavily API key is set
if not os.getenv("TAVILY_API_KEY"):
    print("❌ TAVILY_API_KEY not found in environment variables")
    sys.exit(1)

# Import and test
from langgraph_inspector_rag import query_inspector_rag

print("🧪 Testing single query with debug output\n")

# Test with a query that should trigger web search
query = "What are the latest best practices for inspecting Federal Pacific panels?"
print(f"📝 Query: {query}")

# Run with limited recursion to avoid timeouts
result = query_inspector_rag(query, thread_id="debug_test")

print(f"\n📊 Result Summary:")
print(f"   - Success: {result['success']}")
print(f"   - Response length: {len(result.get('response', ''))}")
print(f"   - Sources: {len(result.get('sources', []))}")

if result['success']:
    print(f"\n💬 Response:")
    print(result.get('response', 'No response'))
    
    if result.get('sources'):
        print(f"\n📚 Sources:")
        for i, source in enumerate(result['sources'][:5], 1):
            print(f"   {i}. {source.get('source', 'Unknown')} (type: {source.get('type', 'unknown')})")

print("\n✨ Debug test complete!")