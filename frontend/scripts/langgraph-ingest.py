#!/usr/bin/env python3
"""LangGraph-based document ingestion with RecursiveCharacterTextSplitter."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document

# PDF processing
import pymupdf4llm

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Configuration
COLLECTION_NAME = 'inspector-standards'
EMBEDDING_MODEL = 'text-embedding-3-small'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Document mapping
DOCUMENT_MAP = {
    "InterNACHI": {
        "path": "../../docs/data/SOP/InterNACHI SOP.pdf",
        "source": "InterNACHI Standards of Practice",
        "category": "Standards",
        "description": "International Association of Certified Home Inspectors Standards of Practice"
    },
    "NCHILB": {
        "path": "../../docs/data/SOP/NCHILB NORTH CAROLINA HOME INSPECTOR LICENSURE BOARD.pdf", 
        "source": "NC Home Inspector Licensure Board",
        "category": "Regulations",
        "description": "North Carolina Home Inspector Licensure Board Standards"
    },
    "2024_nc_collection": {
        "path": "../../docs/data/ North Carolina Building & Inspection Codes /2024_nc_collection.pdf",
        "source": "NC Building Codes 2024",
        "category": "Building Codes",
        "description": "North Carolina Building and Inspection Codes 2024"
    }
}

# Initialize clients
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

# Initialize text splitter - CONSISTENT for all documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n", "\n", ". ", ".", " ", ""]
)

def initialize_collection():
    """Initialize or recreate the Qdrant collection."""
    try:
        # Try to delete existing collection
        qdrant_client.delete_collection(COLLECTION_NAME)
        print(f"🗑️  Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        print(f"📋 No existing collection to delete")
    
    # Create new collection
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"✅ Created new collection: {COLLECTION_NAME}")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pymupdf4llm for better formatting."""
    try:
        # Use pymupdf4llm for better text extraction
        text = pymupdf4llm.to_markdown(file_path)
        print(f"  ✅ Extracted {len(text)} characters using pymupdf4llm")
        return text
    except Exception as e:
        print(f"  ❌ PDF extraction failed: {e}")
        raise

def process_document(doc_key: str, doc_info: Dict[str, Any]) -> List[Document]:
    """Process a single document and return LangChain Document objects."""
    print(f"\n📄 Processing: {doc_info['description']}")
    
    # Construct full path
    file_path = os.path.join(os.path.dirname(__file__), doc_info['path'])
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []
    
    print(f"  📂 File: {file_path}")
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    print(f"  📊 Size: {file_size:.1f}MB")
    
    # Extract text
    try:
        text = extract_text_from_pdf(file_path)
    except Exception as e:
        print(f"❌ Failed to extract text: {e}")
        return []
    
    # Clean text
    text = text.replace('\x00', '').strip()
    print(f"  📝 Cleaned text: {len(text)} characters")
    
    # Split text using RecursiveCharacterTextSplitter
    print(f"  ✂️  Splitting with RecursiveCharacterTextSplitter...")
    print(f"      Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    
    chunks = text_splitter.split_text(text)
    print(f"  ✅ Created {len(chunks)} chunks")
    
    # Create Document objects with consistent metadata
    documents = []
    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) > 50:  # Only include substantial chunks
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": doc_info["source"],
                    "document_name": doc_info["source"],
                    "document_type": doc_info["category"],
                    "category": doc_info["category"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_name": os.path.basename(file_path),
                    "extraction_method": "RecursiveCharacterTextSplitter"
                }
            )
            documents.append(doc)
    
    print(f"  📋 Final documents: {len(documents)} (filtered)")
    return documents

def ingest_documents(doc_keys: List[str] = None):
    """Ingest documents using LangGraph-compatible approach."""
    print("🚀 Starting LangGraph Document Ingestion\n")
    
    # Initialize collection
    initialize_collection()
    
    # Process specified documents or all
    if doc_keys is None:
        doc_keys = list(DOCUMENT_MAP.keys())
    
    all_documents = []
    
    for doc_key in doc_keys:
        if doc_key not in DOCUMENT_MAP:
            print(f"❌ Unknown document key: {doc_key}")
            continue
            
        doc_info = DOCUMENT_MAP[doc_key]
        documents = process_document(doc_key, doc_info)
        all_documents.extend(documents)
    
    if not all_documents:
        print("❌ No documents to ingest")
        return
    
    print(f"\n📊 Total documents to ingest: {len(all_documents)}")
    
    # Create vector store and add documents
    print("🔄 Creating vector store and adding documents...")
    try:
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
        )
        
        # Add documents in batches
        batch_size = 50
        for i in range(0, len(all_documents), batch_size):
            batch = all_documents[i:i + batch_size]
            print(f"  📦 Processing batch {i//batch_size + 1}/{(len(all_documents) + batch_size - 1)//batch_size} ({len(batch)} docs)")
            
            vector_store.add_documents(batch)
            
        print(f"✅ Successfully ingested {len(all_documents)} document chunks")
        
        # Verify ingestion
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        print(f"📈 Final collection size: {collection_info.points_count} points")
        
        # Show source breakdown
        print(f"\n📚 Documents by source:")
        source_counts = {}
        for doc in all_documents:
            source = doc.metadata["source"]
            source_counts[source] = source_counts.get(source, 0) + 1
        
        for source, count in source_counts.items():
            print(f"  - {source}: {count} chunks")
            
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) > 1:
        doc_key = sys.argv[1]
        if doc_key in DOCUMENT_MAP:
            print(f"📄 Ingesting single document: {doc_key}")
            ingest_documents([doc_key])
        else:
            print(f"❌ Unknown document: {doc_key}")
            print(f"Available documents: {', '.join(DOCUMENT_MAP.keys())}")
    else:
        print("📚 Ingesting all documents")
        ingest_documents()

if __name__ == "__main__":
    main()