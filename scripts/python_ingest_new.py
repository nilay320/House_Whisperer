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
from typing import Dict, List, Any
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.document_loaders import PyMuPDFLoader

# Qdrant direct client (not LangChain wrapper to avoid issues)
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Configuration
COLLECTION_NAME = 'inspector-standards-postmidterm'
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

# Text splitter - consistent with backend
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n", "\n", ". ", ".", " ", ""]
)

def ensure_collection_exists():
    """Ensure the collection exists."""
    try:
        collection = qdrant_client.get_collection(COLLECTION_NAME)
        print(f"✅ Collection exists: {COLLECTION_NAME} ({collection.points_count} points)")
        return True
    except Exception:
        print(f"📋 Creating collection: {COLLECTION_NAME}")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print(f"✅ Created collection: {COLLECTION_NAME}")
        return True

def cleanup_document_chunks(source_name: str) -> int:
    """
    Delete all chunks for a specific document source.
    Returns number of chunks deleted.
    """
    print(f"🧹 Cleaning up existing chunks for: '{source_name}'")
    
    try:
        # Get all points first (without filter since filter API is broken)
        all_points = []
        offset = None
        
        while True:
            result = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                offset=offset,
                with_payload=True
            )
            
            if not result[0]:  # No more points
                break
                
            # Filter points by source in Python (since Qdrant filter is broken)
            matching_points = [
                point.id for point in result[0] 
                if point.payload.get("source") == source_name
            ]
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
                    collection_name=COLLECTION_NAME,
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

def ingest_document(doc_key: str) -> int:
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
    
    # STEP 1: CLEANUP - Delete existing chunks
    cleanup_document_chunks(doc_info['source'])
    
    # STEP 2: EXTRACT TEXT
    print(f"📝 Extracting text from PDF...")
    text = extract_text_from_pdf(file_path)
    print(f"   Extracted: {len(text)} characters")
    
    # STEP 3: CHUNK TEXT
    print(f"✂️  Chunking text (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
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
                    "extraction_method": "RecursiveCharacterTextSplitter"
                }
            )
            points.append(point)
        
        # Upload batch with error handling
        try:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
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

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python python_ingest.py <document_key>")
        print(f"Available documents: {', '.join(DOCUMENTS.keys())}")
        sys.exit(1)
    
    doc_key = sys.argv[1]
    
    try:
        print("🚀 Python Document Ingestion with Cleanup")
        print(f"🎯 Target: {doc_key}")
        
        # Ensure collection exists
        ensure_collection_exists()
        
        # Ingest document
        chunks_count = ingest_document(doc_key)
        
        # Final status
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
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