#!/usr/bin/env python3
"""Test the Python chat API with real requests."""

import requests
import json
import sys
import time

def test_health_check(base_url):
    """Test the health endpoint."""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data['message']}")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

def test_chat_endpoint(base_url, message):
    """Test the chat endpoint with streaming."""
    print(f"💬 Testing chat with: '{message}'")
    
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={"message": message},
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ Chat request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        print("   📡 Receiving streaming response...")
        
        chunks_received = 0
        content_chunks = []
        sources = None
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        
                        if 'content' in data:
                            content_chunks.append(data['content'])
                            chunks_received += 1
                            
                        if 'sources' in data:
                            sources = data['sources']
                            print(f"   📚 Received {len(sources)} sources")
                            
                        if data.get('done'):
                            break
                            
                    except json.JSONDecodeError:
                        print(f"   ⚠️  Couldn't parse JSON: {data_str}")
        
        full_response = ''.join(content_chunks)
        
        print(f"   ✅ Received {chunks_received} content chunks")
        print(f"   📝 Response length: {len(full_response)} characters")
        print(f"   🔗 Sources: {[s['source'] for s in sources] if sources else 'None'}")
        
        if len(full_response) > 100:
            print(f"   💭 Response preview: {full_response[:100]}...")
        else:
            print(f"   💭 Full response: {full_response}")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Chat test error: {e}")
        return False

def main():
    """Run the tests."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🧪 Testing Python Chat API at {base_url}\n")
    
    # Test health check
    if not test_health_check(base_url):
        print("❌ Health check failed, aborting tests")
        return
    
    print()
    
    # Test chat endpoint with different queries
    test_queries = [
        "What are the requirements for electrical inspections?",
        "How often should HVAC systems be inspected?",
        "What should I look for when inspecting a roof?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)}")
        print(f"{'='*60}")
        
        if not test_chat_endpoint(base_url, query):
            print(f"❌ Test {i} failed")
        else:
            print(f"✅ Test {i} passed")
        
        if i < len(test_queries):
            print("\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)
    
    print(f"\n🎉 All tests completed!")

if __name__ == "__main__":
    main()