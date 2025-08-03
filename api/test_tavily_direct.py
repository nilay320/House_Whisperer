#!/usr/bin/env python3
"""Direct test of Tavily API to see what it returns."""

import os
from dotenv import load_dotenv
from tavily import TavilyClient
import json

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

# Get API key
api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    print("❌ TAVILY_API_KEY not found")
    exit(1)

# Create client
client = TavilyClient(api_key=api_key)

# Test search
query = "home inspection What are the latest best practices for inspecting Federal Pacific panels? North Carolina"
print(f"🔍 Searching for: {query}\n")

response = client.search(
    query=query,
    max_results=3,
    include_raw_content=True,
    search_depth="advanced"
)

# Show raw response structure
print("📦 Raw response keys:", list(response.keys()))
print(f"📊 Number of results: {len(response.get('results', []))}\n")

# Examine first result in detail
if response.get('results'):
    first = response['results'][0]
    print("🔍 First result structure:")
    print(f"   Keys: {list(first.keys())}")
    print(f"   Title: {first.get('title', 'NO TITLE')[:60]}...")
    print(f"   URL: {first.get('url', 'NO URL')}")
    print(f"   Score: {first.get('score', 'NO SCORE')}")
    print(f"   Content preview: {first.get('content', 'NO CONTENT')[:200]}...")
    
    # Check if raw_content exists and is different
    if 'raw_content' in first:
        print(f"   Raw content length: {len(first['raw_content'])}")
        print(f"   Raw != Content: {first['raw_content'] != first['content']}")
    
    print("\n📝 Content comparison:")
    print(f"Content (first 500 chars):\n{first.get('content', '')[:500]}\n")
    print(f"Raw content (first 500 chars):\n{first.get('raw_content', '')[:500]}\n")
    
    # Show all results briefly
    print("\n📊 All results summary:")
    for i, result in enumerate(response['results']):
        print(f"{i+1}. Score: {result.get('score', 0):.3f} - {result.get('title', '')[:60]}...")
        print(f"   Content preview: {result.get('content', '')[:150]}...")