#!/usr/bin/env python3
"""
Debug script to investigate BM25 and Ensemble failures for token chunking strategy.
"""

import os
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# Set up Qdrant client
qdrant_client = QdrantClient(
    url="https://c95924f4-831b-407f-be42-8e424740487b.us-east-1-0.aws.cloud.qdrant.io",
    api_key=os.environ["QDRANT_API_KEY"],
)

def fetch_docs_for_label_from_qdrant(experiment_label: str, max_docs: int | None = 500):
    """Debug version of the function to see what's happening."""
    docs = []
    offset = None
    fetched = 0
    total_scanned = 0
    
    print(f"🔍 Fetching docs for label: {experiment_label}")
    
    while True:
        batch, offset = qdrant_client.scroll(
            collection_name="post_midterm_R",
            limit=1000,
            offset=offset,
            with_payload=["content", "experiment_label"],
        )
        if not batch:
            break
            
        total_scanned += len(batch)
        print(f"  Scanned {total_scanned} total points...")
        
        for pt in batch:
            payload = pt.payload or {}
            if payload.get("experiment_label") == experiment_label:
                text = payload.get("content", "")
                if text and text.strip():
                    docs.append(Document(page_content=text, metadata={}))
                    fetched += 1
                    if max_docs and fetched >= max_docs:
                        print(f"  ✅ Found {fetched} docs (hit max_docs limit)")
                        return docs
        if not offset:
            break
    
    print(f"  ✅ Found {fetched} docs for label '{experiment_label}'")
    return docs

def test_bm25_creation(experiment_label: str):
    """Test BM25 creation for a specific label."""
    print(f"\n🧪 Testing BM25 creation for: {experiment_label}")
    
    # Fetch docs
    valid_docs = fetch_docs_for_label_from_qdrant(experiment_label, max_docs=500)
    
    if not valid_docs:
        print(f"❌ No documents found for label: {experiment_label}")
        return None
    
    print(f"📄 Found {len(valid_docs)} documents")
    
    # Check document content
    total_chars = sum(len(doc.page_content) for doc in valid_docs)
    avg_chars = total_chars / len(valid_docs)
    print(f"📊 Document stats: avg={avg_chars:.1f} chars, total={total_chars:,} chars")
    
    # Sample first few docs
    print("\n📋 Sample documents:")
    for i, doc in enumerate(valid_docs[:3]):
        preview = doc.page_content[:200].replace('\n', ' ')
        print(f"  {i+1}. {preview}...")
    
    try:
        # Try to create BM25
        bm25_retriever = BM25Retriever.from_documents(valid_docs)
        bm25_retriever.k = 10
        print(f"✅ BM25 created successfully with k={bm25_retriever.k}")
        
        # Test retrieval
        test_query = "What are the requirements for GFCI protection?"
        try:
            results = bm25_retriever.invoke(test_query)
            print(f"✅ BM25 retrieval test successful: {len(results)} results")
            return bm25_retriever
        except Exception as e:
            print(f"❌ BM25 retrieval test failed: {e}")
            return None
            
    except Exception as e:
        print(f"❌ BM25 creation failed: {e}")
        return None

def test_ensemble_creation(naive_retriever, bm25_retriever):
    """Test Ensemble creation."""
    print(f"\n🧪 Testing Ensemble creation")
    
    try:
        ensemble_retriever = EnsembleRetriever(
            retrievers=[naive_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )
        print("✅ Ensemble created successfully")
        
        # Test retrieval
        test_query = "What are the requirements for GFCI protection?"
        try:
            results = ensemble_retriever.invoke(test_query)
            print(f"✅ Ensemble retrieval test successful: {len(results)} results")
            return ensemble_retriever
        except Exception as e:
            print(f"❌ Ensemble retrieval test failed: {e}")
            return None
            
    except Exception as e:
        print(f"❌ Ensemble creation failed: {e}")
        return None

def main():
    """Main debugging function."""
    print("🔧 Debugging BM25 and Ensemble issues for token chunking")
    
    # Test all labels
    labels_to_test = [
        "heading_semantic_pack_600_80_hsp_600_80",
        "recursive_1000_200_rec_1", 
        "token_512_64_tok_384_64"
    ]
    
    for label in labels_to_test:
        print(f"\n{'='*60}")
        print(f"Testing label: {label}")
        print(f"{'='*60}")
        
        # Test BM25
        bm25_retriever = test_bm25_creation(label)
        
        if bm25_retriever:
            # Test Ensemble (would need naive_retriever in real scenario)
            print("⚠️ Ensemble test skipped (needs naive_retriever)")
        else:
            print("❌ Cannot test Ensemble (BM25 failed)")
    
    print(f"\n{'='*60}")
    print("Debugging complete")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
