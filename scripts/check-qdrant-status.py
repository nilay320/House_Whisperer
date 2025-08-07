#!/usr/bin/env python3
"""Check Qdrant collection status and points."""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Initialize client
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

COLLECTION_NAME = 'inspector-standards'

def check_collection_status():
    """Check the collection status and point count."""
    print("🔍 Checking Qdrant Collection Status\n")
    
    try:
        # Get collection info
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        print(f"📊 Collection: {COLLECTION_NAME}")
        print(f"📈 Points count: {collection_info.points_count}")
        print(f"📋 Status: {collection_info.status}")
        print(f"🔧 Config: {collection_info.config}")
        
        # Try to scroll and see actual points
        print(f"\n🔍 Checking actual points in collection...")
        
        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=5,
            with_payload=True
        )
        
        points = scroll_result[0]  # points are in first element
        
        print(f"📋 Found {len(points)} points in scroll result")
        
        if points:
            print(f"\n📄 Sample points:")
            for i, point in enumerate(points[:3], 1):
                print(f"   {i}. ID: {point.id}")
                print(f"      Source: {point.payload.get('source', 'Unknown')}")
                print(f"      Content: {point.payload.get('content', '')[:100]}...")
                print()
        else:
            print("❌ No points found in scroll result")
            
        # Check if collection is empty
        if collection_info.points_count == 0:
            print("⚠️  Collection appears to be empty")
            print("🔄 This might be a sync issue or the ingestion failed")
        
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_collection_status()