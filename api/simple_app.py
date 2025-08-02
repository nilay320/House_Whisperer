#!/usr/bin/env python3
"""Simple FastAPI server for testing the React app."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

# Add the frontend scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend', 'scripts'))

app = FastAPI(title="Inspector RAG API")

# Enable CORS for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RAGChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = "default"

@app.post("/api/chat")
async def chat(request: RAGChatRequest):
    """Chat endpoint that calls our Python LangGraph RAG system."""
    try:
        # Import the RAG function from our scripts
        from langgraph_inspector_rag import query_inspector_rag
        
        # Query the RAG system
        result = query_inspector_rag(request.message, request.sessionId)
        
        return {
            "answer": result,
            "status": "success"
        }
        
    except ImportError as e:
        return {
            "answer": f"RAG system temporarily unavailable. You asked: '{request.message}'. Import error: {str(e)}",
            "status": "error"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Inspector RAG API is running"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Inspector RAG API server...")
    print("📡 API will be available at: http://localhost:8000")
    print("🔗 React app should connect automatically")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")