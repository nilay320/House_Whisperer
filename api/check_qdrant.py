#!/usr/bin/env python3
"""
Check Qdrant database for narratives
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def check_qdrant():
    """Check if Qdrant has any narratives"""
    
    qdrant_url = os.getenv('QDRANT_URL', '').strip()
    qdrant_key = os.getenv('QDRANT_API_KEY', '').strip()
    collection = os.getenv('QDRANT_COLLECTION', 'narratives_v1')
    
    if not qdrant_url or not qdrant_key:
        print("❌ Qdrant not configured")
        return
    
    print(f"🔍 Checking Qdrant database...")
    print(f"   URL: {qdrant_url[:50]}...")
    print(f"   Collection: {collection}")
    
    try:
        # Get collection info
        response = httpx.get(
            f"{qdrant_url}/collections/{collection}",
            headers={"api-key": qdrant_key},
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                result = data['result']
                point_count = result.get('points_count', 0)
                print(f"\n✅ Collection '{collection}' exists")
                print(f"   • Points count: {point_count}")
                print(f"   • Vectors size: {result.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'unknown')}")
                
                if point_count > 0:
                    # Try to scroll some points to see what's in there
                    scroll_response = httpx.post(
                        f"{qdrant_url}/collections/{collection}/points/scroll",
                        headers={"api-key": qdrant_key},
                        json={"limit": 5, "with_payload": True},
                        timeout=10.0
                    )
                    
                    if scroll_response.status_code == 200:
                        scroll_data = scroll_response.json()
                        if 'result' in scroll_data and 'points' in scroll_data['result']:
                            points = scroll_data['result']['points']
                            print(f"\n📝 Sample narratives (showing {len(points)} of {point_count}):")
                            for i, point in enumerate(points, 1):
                                payload = point.get('payload', {})
                                narrative = payload.get('narrative', '')[:100]
                                section = payload.get('section', 'unknown')
                                print(f"   {i}. Section: {section}")
                                print(f"      Narrative: {narrative}...")
                else:
                    print("\n⚠️  Collection is empty - no narratives stored")
            else:
                print(f"❌ Unexpected response format: {data}")
        elif response.status_code == 404:
            print(f"\n❌ Collection '{collection}' not found")
            print("   This explains why no narratives are being found!")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking Qdrant: {e}")

if __name__ == "__main__":
    check_qdrant()