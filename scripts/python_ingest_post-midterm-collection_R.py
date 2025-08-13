#!/usr/bin/env python3
"""
Python ingestion script with working cleanup.
Standardized to match our Python backend.
Fixed: Uses UUID-based IDs to prevent collision issues.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import argparse

# LangChain imports
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter,
)
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader

# Qdrant direct client (not LangChain wrapper to avoid issues)
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Configuration
COLLECTION_NAME = 'post_midterm_R'
EMBEDDING_MODEL = 'text-embedding-3-small'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Document mapping
DOCUMENTS = {
    "InterNACHI": {
        "path": "../docs/data/SOP/InterNACHI SOP.pdf",
        "source": "InterNACHI Standards of Practice",
        "category": "Standards"
    },
    "NCHILB": {
        "path": "../docs/data/SOP/NCHILB NORTH CAROLINA HOME INSPECTOR LICENSURE BOARD.pdf",
        "source": "NC Home Inspector Licensure Board", 
        "category": "Regulations"
    },
    "NC_Codes": {
        "path": "../docs/data/NC_Building_Inspection_Codes/2024_nc_collection_no_footer.pdf",
        "source": "NC Building Codes 2024",
        "category": "Building Codes"
    }
}

# Initialize clients
print("🔧 Initializing clients...")
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

def build_text_splitter(
    strategy: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: Optional[List[str]] = None,
):
    """Create a text splitter by strategy.

    Supported strategies:
      - recursive: hierarchical character splitter (default)
      - character: simple character splitter using provided separators
      - token: token-based splitter (uses tiktoken-compatible tokenizer)
    """
    normalized_strategy = (strategy or "").strip().lower() or "recursive"
    chosen_separators = separators if separators is not None else ["\n\n", "\n", ". ", ".", " ", ""]

    if normalized_strategy == "character":
        return CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=chosen_separators,
        )
    if normalized_strategy == "token":
        # TokenTextSplitter ignores custom separators; splits on token count
        return TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    # Default: recursive
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
        separators=chosen_separators,
    )

def ensure_collection_exists(collection_name: str):
    """Ensure the collection exists."""
    try:
        collection = qdrant_client.get_collection(collection_name)
        print(f"✅ Collection exists: {collection_name} ({collection.points_count} points)")
        return True
    except Exception:
        print(f"📋 Creating collection: {collection_name}")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"✅ Created collection: {collection_name}")
        return True

def cleanup_document_chunks(source_name: str, experiment_label: Optional[str] = None, collection_name: str = COLLECTION_NAME) -> int:
    """
    Delete all chunks for a specific document source.
    Returns number of chunks deleted.
    """
    label_msg = f", label='{experiment_label}'" if experiment_label else ""
    print(f"🧹 Cleaning up existing chunks for: '{source_name}'{label_msg}")
    
    try:
        # Get all points first (without filter since filter API is broken)
        all_points = []
        offset = None
        
        while True:
            result = qdrant_client.scroll(
                collection_name=collection_name,
                limit=1000,
                offset=offset,
                with_payload=True
            )
            
            if not result[0]:  # No more points
                break
                
            # Filter points by source in Python (since Qdrant filter is broken)
            matching_points = []
            for point in result[0]:
                payload = point.payload or {}
                if payload.get("source") != source_name:
                    continue
                if experiment_label is not None and payload.get("experiment_label") != experiment_label:
                    continue
                matching_points.append(point.id)
            all_points.extend(matching_points)
            
            offset = result[1]  # next_page_offset
            if not offset:
                break
        
        if all_points:
            # Delete in batches
            batch_size = 100
            deleted_count = 0
            
            for i in range(0, len(all_points), batch_size):
                batch = all_points[i:i + batch_size]
                qdrant_client.delete(
                    collection_name=collection_name,
                    points_selector=batch
                )
                deleted_count += len(batch)
                print(f"  🗑️  Deleted batch: {len(batch)} chunks")
            
            print(f"✅ Cleanup complete: {deleted_count} chunks deleted for '{source_name}'")
            return deleted_count
        else:
            print(f"ℹ️  No existing chunks found for: '{source_name}'")
            return 0
            
    except Exception as e:
        print(f"❌ Cleanup failed for '{source_name}': {e}")
        raise

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using LangChain PyMuPDFLoader."""
    try:
        print(f"   Using PyMuPDFLoader for extraction...")
        loader = PyMuPDFLoader(file_path)
        documents = loader.load()
        
        # Combine all pages into single text
        full_text = ""
        for doc in documents:
            full_text += doc.page_content + "\n\n"
        
        # Clean up text
        text = full_text.replace('\x00', '').strip()
        print(f"   Extracted: {len(text)} characters from {len(documents)} pages")
        return text
            
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")
        raise

def ingest_document(doc_key: str, text_splitter, experiment_label: Optional[str] = None, collection_name: str = COLLECTION_NAME) -> int:
    """
    Ingest a single document with cleanup.
    Returns number of chunks ingested.
    """
    if doc_key not in DOCUMENTS:
        raise ValueError(f"Unknown document: {doc_key}. Available: {list(DOCUMENTS.keys())}")
    
    doc_info = DOCUMENTS[doc_key]
    print(f"\n📄 Processing: {doc_key}")
    print(f"   Source: {doc_info['source']}")
    print(f"   Category: {doc_info['category']}")
    
    # Get file path
    file_path = os.path.join(os.path.dirname(__file__), doc_info['path'])
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"   File: {file_path} ({file_size:.1f}MB)")
    
    # STEP 1: CLEANUP - Delete existing chunks for this experiment label only
    cleanup_document_chunks(doc_info['source'], experiment_label=experiment_label, collection_name=collection_name)
    
    # STEP 2: EXTRACT TEXT
    print(f"📝 Extracting text from PDF...")
    text = extract_text_from_pdf(file_path)
    print(f"   Extracted: {len(text)} characters")
    
    # STEP 3: CHUNK TEXT
    print(f"✂️  Chunking text (size={text_splitter._chunk_size if hasattr(text_splitter, '_chunk_size') else CHUNK_SIZE}, overlap={text_splitter._chunk_overlap if hasattr(text_splitter, '_chunk_overlap') else CHUNK_OVERLAP})...")
    chunks = text_splitter.split_text(text)
    print(f"   Created: {len(chunks)} chunks")
    
    # STEP 4: CREATE EMBEDDINGS & POINTS
    print(f"🔄 Creating embeddings and uploading...")
    
    # Note: Using UUID-based IDs to prevent collisions
    # Previously used sequential IDs based on points_count which caused overwrites
    
    # Process in batches - optimized for performance
    batch_size = 25  # Sweet spot: reduces API calls while keeping payload reasonable
    total_uploaded = 0
    failed_batches = []
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print(f"   📦 Batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
        
        # Create embeddings for batch
        batch_embeddings = embeddings.embed_documents(batch_chunks)
        
        # Create points
        points = []
        for j, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
            # Generate unique UUID for each point to prevent ID collisions
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "content": chunk,
                    "source": doc_info["source"],
                    "document_name": doc_info["source"],
                    "category": doc_info["category"],
                    "chunk_index": i + j,
                    "total_chunks": len(chunks),
                    "file_name": os.path.basename(file_path),
                    # Metadata to capture chunking strategy used for experiment tracking
                    "chunking_strategy": type(text_splitter).__name__,
                    "chunk_size": getattr(text_splitter, "_chunk_size", CHUNK_SIZE),
                    "chunk_overlap": getattr(text_splitter, "_chunk_overlap", CHUNK_OVERLAP),
                    "separators": getattr(text_splitter, "separators", None),
                    "experiment_label": experiment_label,
                    "extraction_method": "PyMuPDFLoader",
                }
            )
            points.append(point)
        
        # Upload batch with error handling
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True  # Wait for operation to complete
            )
            
            total_uploaded += len(batch_chunks)
            print(f"   ✅ Uploaded batch {batch_num}")
            
            # Add small delay for large documents to avoid rate limiting
            if len(chunks) > 1000 and batch_num % 20 == 0:
                import time
                time.sleep(0.5)
                print(f"   ⏸️  Rate limit pause... ({total_uploaded}/{len(chunks)} chunks uploaded)")
                
        except Exception as e:
            print(f"   ❌ Failed batch {batch_num}: {e}")
            failed_batches.append(batch_num)
    
    if failed_batches:
        print(f"⚠️  Warning: {len(failed_batches)} batches failed: {failed_batches[:10]}...")
    
    print(f"🎉 Completed {doc_key}: {total_uploaded} chunks ingested")
    return total_uploaded

def _parse_separators_arg(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    text = raw.strip()
    # Accept JSON-like list or comma-separated values
    if text.startswith("[") and text.endswith("]"):
        # Remove brackets and split on commas, keep escape sequences
        inner = text[1:-1]
        items = [s.strip().strip('"\'') for s in inner.split(",")]
        return [
            i.encode("utf-8").decode("unicode_escape") for i in items if i != ""
        ]
    # Comma-separated
    parts = [p.strip() for p in text.split(",")]
    return [p.encode("utf-8").decode("unicode_escape") for p in parts if p != ""]


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Ingest a document into Qdrant with configurable chunking.")
    parser.add_argument("document_key", choices=list(DOCUMENTS.keys()), help="Which document to ingest")
    parser.add_argument("--strategy", choices=["recursive", "character", "token"], default="recursive", help="Text splitting strategy")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Chunk size for splitting")
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP, help="Overlap between chunks")
    parser.add_argument("--experiment-label", type=str, default=None, help="Experiment label to tag points and scope cleanup (enables A/B tests in one collection)")
    parser.add_argument(
        "--separators",
        type=str,
        default=None,
        help="Custom separators as comma-separated list or JSON list (e.g., [\\n\\n, \\n, . , ' ']) — only used for recursive/character",
    )
    parser.add_argument("--collection-name", type=str, default=COLLECTION_NAME, help="Override target collection name")
    parser.add_argument("--per-experiment-collection", action="store_true", help="If set, use a separate collection per experiment label (appends label to collection name)")

    args = parser.parse_args()

    try:
        print("🚀 Python Document Ingestion with Cleanup")
        print(f"🎯 Target: {args.document_key}")
        print(f"🧪 Strategy: {args.strategy} | size={args.chunk_size}, overlap={args.chunk_overlap}")

        # Build splitter
        custom_separators = _parse_separators_arg(args.separators)
        splitter = build_text_splitter(
            strategy=args.strategy,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            separators=custom_separators,
        )

        # Determine effective collection name
        effective_collection_name = args.collection_name
        if args.per_experiment_collection and args.experiment_label:
            effective_collection_name = f"{args.collection_name}__{args.experiment_label}"

        print(f"📚 Collection: {effective_collection_name}")

        # Ensure collection exists
        ensure_collection_exists(effective_collection_name)

        # Ingest document
        chunks_count = ingest_document(
            args.document_key,
            splitter,
            experiment_label=args.experiment_label,
            collection_name=effective_collection_name,
        )

        # Final status
        collection_info = qdrant_client.get_collection(effective_collection_name)
        print(f"\n✅ SUCCESS!")
        print(f"📊 Total collection size: {collection_info.points_count} points")
        print(f"📈 This session added: {chunks_count} chunks")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()