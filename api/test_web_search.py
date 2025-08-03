#!/usr/bin/env python3
"""Test script for web search integration."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

# Test if Tavily API key is set
if not os.getenv("TAVILY_API_KEY"):
    print("❌ TAVILY_API_KEY not found in environment variables")
    print("Please add TAVILY_API_KEY to your frontend/.env.local file")
    print("Get your free API key from https://tavily.com")
    sys.exit(1)

# Import and test the tools
from web_search_tools import test_web_search
from langgraph_inspector_rag import query_inspector_rag

print("🧪 Testing Web Search Integration\n")

# Test 1: Direct web search tool
print("=" * 60)
print("Test 1: Direct Web Search Tool")
print("=" * 60)
test_web_search()

# Test 2: Full RAG with web search
print("\n" + "=" * 60)
print("Test 2: Full RAG Query with Web Search")
print("=" * 60)

test_queries = [
    "What are the latest best practices for inspecting Federal Pacific panels?",
    "Are there any recalls on Zinsco electrical panels?",
    "What do other inspectors recommend for roof flashing inspection?"
]

for query in test_queries:
    print(f"\n📝 Query: {query}")
    result = query_inspector_rag(query, thread_id="test_web")
    
    if result["success"]:
        print(f"✅ Success!")
        print(f"   - Context docs: {result['context_docs']}")
        print(f"   - Sources: {len(result['sources'])}")
        
        # Check if web sources were used
        web_sources = [s for s in result['sources'] if s.get('type') == 'web_resource']
        if web_sources:
            print(f"   - Web sources found: {len(web_sources)}")
            for ws in web_sources[:2]:
                print(f"     • {ws['source']}")
    else:
        print(f"❌ Failed: {result['error']}")

print("\n✨ Web search integration test complete!")