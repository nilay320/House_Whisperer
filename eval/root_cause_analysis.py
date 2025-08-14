#!/usr/bin/env python3
"""
Root Cause Analysis: BM25 and Ensemble NaN Issues for Token Chunking Strategy
"""

import os
import pandas as pd
import numpy as np
from qdrant_client import QdrantClient
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

# Use environment variables directly
qdrant_api_key = os.environ.get("QDRANT_API_KEY")
if not qdrant_api_key:
    print("❌ QDRANT_API_KEY not found in environment variables")
    print("Please set QDRANT_API_KEY environment variable or run: source ../.env")
    exit(1)

# Set up Qdrant client
qdrant_client = QdrantClient(
    url="https://c95924f4-831b-407f-be42-8e424740487b.us-east-1-0.aws.cloud.qdrant.io",
    api_key=qdrant_api_key,
)

def analyze_collection_stats():
    """Analyze overall collection statistics."""
    print("🔍 COLLECTION ANALYSIS")
    print("=" * 60)
    
    # Get collection info
    collection_info = qdrant_client.get_collection("post_midterm_R")
    print(f"Total points: {collection_info.points_count}")
    
    # Count documents per experiment_label
    labels = {}
    offset = None
    total_scanned = 0
    
    while True:
        batch, offset = qdrant_client.scroll(
            collection_name="post_midterm_R",
            limit=1000,
            offset=offset,
            with_payload=["experiment_label"],
        )
        if not batch:
            break
            
        total_scanned += len(batch)
        for pt in batch:
            payload = pt.payload or {}
            label = payload.get("experiment_label", "unknown")
            labels[label] = labels.get(label, 0) + 1
            
        if not offset:
            break
    
    print(f"Scanned {total_scanned} points")
    print("\n📊 Documents per experiment_label:")
    for label, count in sorted(labels.items()):
        print(f"  {label}: {count:,} documents")
    
    return labels

def fetch_docs_for_label_from_qdrant(experiment_label: str, max_docs: int | None = 500):
    """Fetch docs for a specific label with detailed analysis."""
    docs = []
    offset = None
    fetched = 0
    total_scanned = 0
    empty_content = 0
    short_content = 0
    
    print(f"\n🔍 Fetching docs for label: {experiment_label}")
    
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
        
        for pt in batch:
            payload = pt.payload or {}
            if payload.get("experiment_label") == experiment_label:
                text = payload.get("content", "")
                
                if not text or not text.strip():
                    empty_content += 1
                    continue
                    
                if len(text.strip()) < 10:
                    short_content += 1
                    continue
                
                docs.append(Document(page_content=text, metadata={}))
                fetched += 1
                if max_docs and fetched >= max_docs:
                    break
                    
        if not offset or (max_docs and fetched >= max_docs):
            break
    
    print(f"  📊 Analysis:")
    print(f"    - Total scanned: {total_scanned:,}")
    print(f"    - Empty content: {empty_content}")
    print(f"    - Short content (<10 chars): {short_content}")
    print(f"    - Valid docs: {fetched}")
    
    return docs

def analyze_document_quality(docs, label):
    """Analyze document quality for BM25 suitability."""
    print(f"\n📋 DOCUMENT QUALITY ANALYSIS: {label}")
    print("-" * 50)
    
    if not docs:
        print("❌ No documents to analyze")
        return False
    
    # Content length analysis
    lengths = [len(doc.page_content.strip()) for doc in docs]
    avg_length = np.mean(lengths)
    min_length = np.min(lengths)
    max_length = np.max(lengths)
    
    print(f"📏 Length statistics:")
    print(f"  - Average: {avg_length:.1f} characters")
    print(f"  - Min: {min_length} characters")
    print(f"  - Max: {max_length} characters")
    
    # Content quality analysis
    empty_docs = sum(1 for doc in docs if not doc.page_content.strip())
    very_short = sum(1 for doc in docs if len(doc.page_content.strip()) < 50)
    short = sum(1 for doc in docs if len(doc.page_content.strip()) < 100)
    
    print(f"📊 Quality breakdown:")
    print(f"  - Empty: {empty_docs}")
    print(f"  - Very short (<50 chars): {very_short}")
    print(f"  - Short (<100 chars): {short}")
    print(f"  - Good length: {len(docs) - short}")
    
    # Sample content analysis
    print(f"\n📋 Sample content (first 3 docs):")
    for i, doc in enumerate(docs[:3]):
        content = doc.page_content.strip()
        preview = content[:200] if len(content) > 200 else content
        print(f"  {i+1}. Length: {len(content)} chars")
        print(f"     Preview: {preview}")
        print()
    
    # Check for BM25 suitability
    suitable_for_bm25 = len(docs) >= 10 and avg_length >= 100
    print(f"✅ BM25 suitability: {'Yes' if suitable_for_bm25 else 'No'}")
    print(f"   - Reason: {'Sufficient docs and content length' if suitable_for_bm25 else 'Too few docs or too short content'}")
    
    return suitable_for_bm25

def test_bm25_creation_and_retrieval(docs, label):
    """Test BM25 creation and retrieval."""
    print(f"\n🧪 BM25 CREATION & RETRIEVAL TEST: {label}")
    print("-" * 50)
    
    if not docs:
        print("❌ No documents provided")
        return None, False
    
    try:
        # Create BM25
        print("🔧 Creating BM25 retriever...")
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = 10
        print(f"✅ BM25 created successfully with k={bm25_retriever.k}")
        
        # Test retrieval with sample queries
        test_queries = [
            "What are the renewal requirements for licenses according to the NC General Statutes?",
            "GFCI protection requirements",
            "electrical safety standards",
            "home inspection requirements"
        ]
        
        retrieval_success = True
        for i, query in enumerate(test_queries, 1):
            try:
                print(f"\n🔍 Test query {i}: '{query}'")
                results = bm25_retriever.invoke(query)
                print(f"  ✅ Retrieved {len(results)} documents")
                
                if len(results) == 0:
                    print("  ⚠️ Warning: No results returned")
                    retrieval_success = False
                else:
                    # Show top result preview
                    top_result = results[0]
                    preview = top_result.page_content[:150] if len(top_result.page_content) > 150 else top_result.page_content
                    print(f"  📄 Top result: {preview}...")
                    
            except Exception as e:
                print(f"  ❌ Retrieval failed: {e}")
                retrieval_success = False
        
        return bm25_retriever, retrieval_success
        
    except Exception as e:
        print(f"❌ BM25 creation failed: {e}")
        return None, False

def test_ensemble_creation(naive_retriever, bm25_retriever, label):
    """Test Ensemble creation."""
    print(f"\n🧪 ENSEMBLE CREATION TEST: {label}")
    print("-" * 50)
    
    if not bm25_retriever:
        print("❌ Cannot create ensemble - BM25 retriever is None")
        return None, False
    
    try:
        print("🔧 Creating Ensemble retriever...")
        ensemble_retriever = EnsembleRetriever(
            retrievers=[naive_retriever, bm25_retriever],
            weights=[0.5, 0.5]
        )
        print("✅ Ensemble created successfully")
        
        # Test retrieval
        test_query = "What are the renewal requirements for licenses according to the NC General Statutes?"
        print(f"\n🔍 Testing ensemble with query: '{test_query}'")
        
        try:
            results = ensemble_retriever.invoke(test_query)
            print(f"✅ Ensemble retrieval successful: {len(results)} results")
            return ensemble_retriever, True
            
        except Exception as e:
            print(f"❌ Ensemble retrieval failed: {e}")
            return ensemble_retriever, False
            
    except Exception as e:
        print(f"❌ Ensemble creation failed: {e}")
        return None, False

def simulate_ragas_evaluation_issue(bm25_retriever, label):
    """Simulate potential RAGAS evaluation issues."""
    print(f"\n🔬 RAGAS EVALUATION SIMULATION: {label}")
    print("-" * 50)
    
    if not bm25_retriever:
        print("❌ No BM25 retriever to test")
        return
    
    # Test with the exact query from your evaluation
    test_query = "What are the renewal requirements for licenses according to the NC General Statutes?"
    
    try:
        print(f"🔍 Testing with evaluation query: '{test_query}'")
        results = bm25_retriever.invoke(test_query)
        print(f"✅ Retrieved {len(results)} documents")
        
        if len(results) == 0:
            print("❌ CRITICAL ISSUE: BM25 returns empty results for evaluation query")
            print("   This would cause RAGAS Context Precision to fail and return NaN")
            return False
        else:
            print("✅ BM25 returns results - issue may be in RAGAS processing")
            
            # Check if results contain relevant content
            relevant_keywords = ["renewal", "license", "requirements", "NC", "statutes"]
            relevant_count = 0
            
            for i, doc in enumerate(results[:3]):
                content_lower = doc.page_content.lower()
                matches = sum(1 for keyword in relevant_keywords if keyword in content_lower)
                print(f"  Doc {i+1}: {matches}/{len(relevant_keywords)} relevant keywords")
                if matches >= 2:
                    relevant_count += 1
            
            print(f"📊 Relevance: {relevant_count}/{min(3, len(results))} docs seem relevant")
            return relevant_count > 0
            
    except Exception as e:
        print(f"❌ Error during evaluation simulation: {e}")
        return False

def main():
    """Main root cause analysis."""
    print("🔧 ROOT CAUSE ANALYSIS: BM25 & Ensemble NaN Issues")
    print("=" * 80)
    
    # Step 1: Collection analysis
    labels = analyze_collection_stats()
    
    # Step 2: Focus on token strategy
    token_label = "token_512_64_tok_384_64"
    
    if token_label not in labels:
        print(f"❌ Label '{token_label}' not found in collection")
        return
    
    print(f"\n🎯 FOCUSING ON PROBLEMATIC LABEL: {token_label}")
    print("=" * 60)
    
    # Step 3: Fetch and analyze token documents
    token_docs = fetch_docs_for_label_from_qdrant(token_label, max_docs=500)
    
    # Step 4: Document quality analysis
    suitable_for_bm25 = analyze_document_quality(token_docs, token_label)
    
    # Step 5: BM25 creation and retrieval test
    bm25_retriever, bm25_success = test_bm25_creation_and_retrieval(token_docs, token_label)
    
    # Step 6: RAGAS evaluation simulation
    if bm25_retriever:
        ragas_compatible = simulate_ragas_evaluation_issue(bm25_retriever, token_label)
    else:
        ragas_compatible = False
    
    # Step 7: Compare with other strategies
    print(f"\n📊 COMPARISON WITH OTHER STRATEGIES")
    print("=" * 60)
    
    comparison_labels = ["heading_semantic_pack_600_80_hsp_600_80", "recursive_1000_200_rec_1"]
    
    for comp_label in comparison_labels:
        if comp_label in labels:
            print(f"\n--- {comp_label} ---")
            comp_docs = fetch_docs_for_label_from_qdrant(comp_label, max_docs=100)  # Smaller sample
            comp_suitable = analyze_document_quality(comp_docs, comp_label)
            comp_bm25, comp_success = test_bm25_creation_and_retrieval(comp_docs, comp_label)
            
            print(f"  BM25 Success: {'✅' if comp_success else '❌'}")
    
    # Step 8: Root cause summary
    print(f"\n🎯 ROOT CAUSE SUMMARY")
    print("=" * 60)
    
    print(f"Token Strategy ({token_label}):")
    print(f"  - Documents available: {len(token_docs)}")
    print(f"  - Suitable for BM25: {'✅' if suitable_for_bm25 else '❌'}")
    print(f"  - BM25 creation: {'✅' if bm25_success else '❌'}")
    print(f"  - RAGAS compatible: {'✅' if ragas_compatible else '❌'}")
    
    if not suitable_for_bm25:
        print(f"\n🔍 ROOT CAUSE: Document quality issues")
        print(f"   - Token chunks may be too small/fragmented for BM25")
        print(f"   - Insufficient content length for keyword matching")
    elif not bm25_success:
        print(f"\n🔍 ROOT CAUSE: BM25 creation/retrieval failure")
        print(f"   - Technical issue with BM25 implementation")
    elif not ragas_compatible:
        print(f"\n🔍 ROOT CAUSE: RAGAS evaluation incompatibility")
        print(f"   - BM25 returns empty results for evaluation queries")
        print(f"   - This causes Context Precision to fail and return NaN")
    else:
        print(f"\n🔍 ROOT CAUSE: Unknown - all tests passed")
    
    print(f"\n💡 RECOMMENDED FIXES:")
    if not suitable_for_bm25:
        print(f"   1. Skip BM25 for token strategy (recommended)")
        print(f"   2. Use larger token chunks for BM25")
        print(f"   3. Implement hybrid approach")
    elif not ragas_compatible:
        print(f"   1. Replace NaN with 0 in analysis")
        print(f"   2. Skip BM25 for token strategy")
        print(f"   3. Improve BM25 corpus quality")

if __name__ == "__main__":
    main()
