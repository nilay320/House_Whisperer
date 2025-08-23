#!/usr/bin/env python3
"""
Direct test of Qdrant connection and narrative retrieval
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load from api/.env
env_path = Path(__file__).parent.parent / "api" / ".env"
load_dotenv(env_path)

def test_qdrant():
    """Test Qdrant connection and search"""
    
    qdrant_url = os.getenv('QDRANT_URL', '').strip()
    qdrant_key = os.getenv('QDRANT_API_KEY', '').strip()
    collection = 'narratives_v1'  # Correct collection name
    
    print(f"🔗 Qdrant URL: {qdrant_url}")
    print(f"🔑 API Key: {'SET' if qdrant_key else 'NOT SET'}")
    print(f"📦 Collection: {collection}")
    print()
    
    if not qdrant_url or not qdrant_key:
        print("❌ Missing Qdrant configuration")
        return
    
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        # Connect to Qdrant
        print("Connecting to Qdrant...")
        qc = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        
        # Get collection info
        print(f"\n📊 Getting info for collection '{collection}'...")
        try:
            info = qc.get_collection(collection_name=collection)
            print(f"✅ Collection exists!")
            print(f"   Points count: {info.points_count}")
            print(f"   Vectors size: {info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else 'unknown'}")
            print(f"   Status: {info.status}")
        except Exception as e:
            print(f"❌ Collection error: {e}")
            # Try to list collections
            print("\n📋 Available collections:")
            collections = qc.get_collections()
            for c in collections.collections:
                print(f"   - {c.name}")
            return
        
        # Try a simple search for Insulation section
        print(f"\n🔍 Testing search in 'insulation_ventilation' section...")
        
        # Create a simple embedding (normally would use OpenAI)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            # Create embedding for insulation query
            test_query = "Attic insulation is only about 4 inches deep insufficient insulation depth"
            emb = client.embeddings.create(
                model=os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small'),
                input=test_query
            )
            vector = emb.data[0].embedding
            
            # Search with insulation_ventilation filter (correct section key from config)
            flt = Filter(must=[
                FieldCondition(key='section', match=MatchValue(value='insulation_ventilation'))
            ])
            
            results = qc.search(
                collection_name=collection,
                query_vector=vector,
                limit=5,
                query_filter=flt
            )
            
            print(f"\n📝 Found {len(results)} results for insulation_ventilation section:")
            for i, r in enumerate(results, 1):
                score = getattr(r, 'score', 0)
                payload = getattr(r, 'payload', {})
                name = payload.get('comment_name', '')[:50]
                text = payload.get('comment_text', '')[:100]
                print(f"\n{i}. Score: {score:.3f}")
                print(f"   Name: {name}")
                print(f"   Text: {text}...")
                
                # Check if this is the 3-4 inch narrative
                full_text = f"{payload.get('comment_name', '')} {payload.get('comment_text', '')}"
                if '3-4 inch' in full_text.lower() or 'three to four inch' in full_text.lower():
                    print(f"   ✅ THIS IS THE TARGET NARRATIVE!")
            
            if len(results) == 0:
                print("   ❌ No results found - check if narratives are loaded in Qdrant")
                
                # Try without filter
                print("\n🔍 Testing search WITHOUT section filter...")
                results_no_filter = qc.search(
                    collection_name=collection,
                    query_vector=vector,
                    limit=5
                )
                
                print(f"   Found {len(results_no_filter)} results without filter")
                if results_no_filter:
                    sections = set()
                    for r in results_no_filter:
                        payload = getattr(r, 'payload', {})
                        section = payload.get('section', 'unknown')
                        sections.add(section)
                    print(f"   Sections found: {', '.join(sections)}")
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Install with: pip install qdrant-client")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qdrant()