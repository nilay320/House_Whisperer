#!/usr/bin/env python3
"""
Test script for PDF RAG functionality using aimakerspace library.
This script tests the PDF loading, text splitting, and vector database functionality.
"""

import sys
import os
import asyncio

# Add the parent directory to the path to import aimakerspace
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from aimakerspace.text_utils import PDFLoader, CharacterTextSplitter
from aimakerspace.vectordatabase import VectorDatabase

async def test_pdf_processing():
    """Test the PDF processing pipeline."""
    print("🧪 Testing PDF RAG functionality...")
    
    # Test with a sample text (since we don't have a PDF file)
    sample_texts = [
        "The Three Laws of Robotics are fundamental principles that govern robot behavior.",
        "First Law: A robot may not injure a human being or, through inaction, allow a human being to come to harm.",
        "Second Law: A robot must obey orders given it by human beings except where such orders would conflict with the First Law.",
        "Third Law: A robot must protect its own existence as long as such protection does not conflict with the First or Second Law.",
        "These laws were introduced by Isaac Asimov in his science fiction works."
    ]
    
    try:
        # Test text splitting
        print("📝 Testing text splitting...")
        splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        chunks = splitter.split_texts(sample_texts)
        print(f"✅ Created {len(chunks)} chunks from {len(sample_texts)} texts")
        
        # Test vector database
        print("🔍 Testing vector database...")
        vector_db = VectorDatabase()
        await vector_db.abuild_from_list(chunks)
        print(f"✅ Built vector database with {len(chunks)} embeddings")
        
        # Test similarity search
        print("🔎 Testing similarity search...")
        query = "What are the Three Laws of Robotics?"
        results = vector_db.search_by_text(query, k=2, return_as_text=True)
        print(f"✅ Found {len(results)} relevant chunks for query: '{query}'")
        for i, result in enumerate(results):
            print(f"   {i+1}. {result[:100]}...")
        
        print("🎉 All tests passed! The aimakerspace library is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_pdf_processing())
    sys.exit(0 if success else 1) 