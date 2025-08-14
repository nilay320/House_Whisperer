#!/usr/bin/env python3
"""
Simple test to check BM25 retrieval for token strategy.
"""

import os
import getpass
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

# Get API key
if "QDRANT_API_KEY" not in os.environ:
    os.environ["QDRANT_API_KEY"] = getpass.getpass("Enter your Qdrant API Key: ")

# Set up Qdrant client
qdrant_client = QdrantClient(
    url="https://c95924f4-831b-407f-be42-8e424740487b.us-east-1-0.aws.cloud.qdrant.io",
    api_key=os.environ["QDRANT_API_KEY"],
)

def fetch_docs_for_label_from_qdrant(experiment_label: str, max_docs: int | None = 500):
    """Fetch docs for a specific label."""
    docs = []
    offset = None
    fetched = 0
    
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
            
        for pt in batch:
            payload = pt.payload or {}
            if payload.get("experiment_label") == experiment_label:
                text = payload.get("content", "")
                if text and text.strip():
                    docs.append(Document(page_content=text, metadata={}))
                    fetched += 1
                    if max_docs and fetched >= max_docs:
                        return docs
        if not offset:
            break
    
    print(f"  ✅ Found {fetched} docs for label '{experiment_label}'")
    return docs

def test_bm25_retrieval(experiment_label: str, test_query: str):
    """Test BM25 retrieval for a specific label."""
    print(f"\n🧪 Testing BM25 for: {experiment_label}")
    
    # Fetch docs
    valid_docs = fetch_docs_for_label_from_qdrant(experiment_label, max_docs=500)
    
    if not valid_docs:
        print(f"❌ No documents found for label: {experiment_label}")
        return None
    
    print(f"📄 Found {len(valid_docs)} documents")
    
    # Check document content quality
    empty_docs = sum(1 for doc in valid_docs if not doc.page_content.strip())
    short_docs = sum(1 for doc in valid_docs if len(doc.page_content.strip()) < 10)
    
    print(f"📊 Document quality: {empty_docs} empty, {short_docs} very short")
    
    # Sample content
    print("\n📋 Sample document content:")
    for i, doc in enumerate(valid_docs[:2]):
        content = doc.page_content.strip()
        preview = content[:200] if len(content) > 200 else content
        print(f"  {i+1}. Length: {len(content)} chars")
        print(f"     Preview: {preview}")
        print()
    
    try:
        # Create BM25
        bm25_retriever = BM25Retriever.from_documents(valid_docs)
        bm25_retriever.k = 10
        print(f"✅ BM25 created successfully with k={bm25_retriever.k}")
        
        # Test retrieval
        print(f"\n🔍 Testing retrieval with query: '{test_query}'")
        results = bm25_retriever.invoke(test_query)
        print(f"✅ Retrieved {len(results)} documents")
        
        # Show top results
        print("\n📋 Top 3 retrieved documents:")
        for i, doc in enumerate(results[:3]):
            content = doc.page_content.strip()
            preview = content[:150] if len(content) > 150 else content
            print(f"  {i+1}. Length: {len(content)} chars")
            print(f"     Preview: {preview}")
            print()
        
        return bm25_retriever
        
    except Exception as e:
        print(f"❌ BM25 creation/retrieval failed: {e}")
        return None

def main():
    """Main test function."""
    print("🔧 Testing BM25 retrieval for token strategy")
    
    # Test query from your evaluation
    test_query = "What are the renewal requirements for licenses according to the NC General Statutes?"
    
    # Test token strategy
    token_label = "token_512_64_tok_384_64"
    bm25_retriever = test_bm25_retrieval(token_label, test_query)
    
    if bm25_retriever:
        print("✅ BM25 retrieval is working - the issue is likely in RAGAS evaluation")
    else:
        print("❌ BM25 retrieval is failing - this explains the NaN values")
    
    # Also test other strategies for comparison
    print(f"\n{'='*60}")
    print("Testing other strategies for comparison:")
    
    other_labels = [
        "heading_semantic_pack_600_80_hsp_600_80",
        "recursive_1000_200_rec_1"
    ]
    
    for label in other_labels:
        print(f"\n--- Testing {label} ---")
        test_bm25_retrieval(label, test_query)

if __name__ == "__main__":
    main()
