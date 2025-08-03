# Import required FastAPI components for building the API
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
# Import Pydantic for data validation and settings management
from pydantic import BaseModel
# Import OpenAI client for interacting with OpenAI's API
from openai import OpenAI
import os
from typing import Optional
import shutil
import sys
from dotenv import load_dotenv

# Load environment variables from .env.local (for local development)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

# Standard imports for PDF processing and text handling
import PyPDF2
from io import BytesIO

# Import our LangGraph RAG system - delay import to avoid initialization issues
LANGGRAPH_AVAILABLE = True

# Standard imports for JSON handling
import json

# Initialize FastAPI application with a title
app = FastAPI(title="OpenAI Chat API")

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"🔑 OPENAI_API_KEY loaded: {'Yes' if OPENAI_API_KEY else 'No'}")
print(f"🔑 Key preview: {OPENAI_API_KEY[:10] if OPENAI_API_KEY else 'Not set'}...")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY not found in environment")
    print(f"❌ Available env vars: {list(os.environ.keys())}")

# Get allowed origins from environment variable or use defaults
# Include Vercel preview URLs and production URL
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://*.vercel.app").split(",")
# Add the actual production URL when known
if os.getenv("VERCEL_URL"):
    ALLOWED_ORIGINS.append(f"https://{os.getenv('VERCEL_URL')}")

# Configure CORS (Cross-Origin Resource Sharing) middleware
# This allows the API to be accessed from different domains/origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# For Vercel serverless: use ephemeral in-memory processing only
# No persistent file storage due to read-only filesystem
PDF_UPLOAD_DIR = "/tmp"  # Use /tmp for temporary file storage

# Global variable to store vector databases for uploaded PDFs
pdf_vector_dbs = {}

# Define the data model for chat requests using Pydantic
# This ensures incoming request data is properly validated
class ChatRequest(BaseModel):
    developer_message: str  # Message from the developer/system
    user_message: str      # Message from the user
    model: Optional[str] = "gpt-4o-mini"  # Optional model selection with default

# Define the data model for PDF chat requests
class PDFChatRequest(BaseModel):
    question: str
    pdf_filename: str
    model: Optional[str] = "gpt-4o-mini"

# Define the data model for RAG chat requests (Inspector standards)
class RAGChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = "default"

# Define the main chat endpoint for LangGraph RAG (Inspector standards) with SSE streaming
@app.post("/api/chat")
async def rag_chat(request: RAGChatRequest):
    try:
        print(f"📧 Received chat request: {request.message}")
        
        if not LANGGRAPH_AVAILABLE:
            # Simple fallback response for testing
            return {
                "answer": f"Hello! You asked: '{request.message}'. The LangGraph RAG system is temporarily unavailable, but I'm here to help with home inspection questions. The backend API is working correctly!",
                "status": "success"
            }
        
        # Import here to avoid circular imports and initialization issues
        try:
            from langgraph_inspector_rag import query_inspector_rag_streaming
        except ImportError as e:
            print(f"❌ Failed to import LangGraph: {e}")
            raise HTTPException(status_code=500, detail=f"LangGraph import failed: {str(e)}")
        
        async def generate_stream():
            """Generate SSE stream with progress updates."""
            import time
            start_time = time.time()
            
            try:
                # Send initial status with timestamp
                initial_data = {
                    "status": "starting", 
                    "message": "Initializing AI agents...", 
                    "timestamp": start_time
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
                
                # Query the streaming LangGraph RAG system
                async for update in query_inspector_rag_streaming(request.message, request.sessionId):
                    if update.get("type") == "progress":
                        # Send progress update with elapsed time
                        elapsed = time.time() - start_time
                        progress_data = {
                            "status": "progress", 
                            "message": update.get("message", ""),
                            "elapsed_seconds": round(elapsed, 2)
                        }
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    elif update.get("type") == "complete":
                        # Send final result via multiple SSE messages to handle large responses
                        total_time = time.time() - start_time
                        response_text = update.get("response", "No response generated")
                        sources = update.get("sources", [])
                        
                        print(f"📤 Streaming complete response ({len(response_text)} chars)")
                        
                        # Send response metadata first
                        metadata = {
                            "status": "response_start",
                            "total_time_seconds": round(total_time, 2),
                            "response_length": len(response_text),
                            "sources_count": len(sources)
                        }
                        yield f"data: {json.dumps(metadata)}\n\n"
                        
                        # Stream response content in chunks
                        chunk_size = 1000  # Reasonable chunk size for SSE
                        for i in range(0, len(response_text), chunk_size):
                            chunk = response_text[i:i + chunk_size]
                            chunk_data = {
                                "status": "response_chunk",
                                "chunk": chunk,
                                "chunk_index": i // chunk_size,
                                "is_final_chunk": (i + chunk_size) >= len(response_text)
                            }
                            yield f"data: {json.dumps(chunk_data)}\n\n"
                        
                        # Send sources separately
                        sources_data = {
                            "status": "sources",
                            "sources": sources
                        }
                        yield f"data: {json.dumps(sources_data)}\n\n"
                        
                        # Send completion signal
                        complete_data = {
                            "status": "complete",
                            "total_time_seconds": round(total_time, 2)
                        }
                        yield f"data: {json.dumps(complete_data)}\n\n"
                        break
                    elif update.get("type") == "error":
                        # Send error
                        error_data = {
                            "status": "error", 
                            "message": update.get("message", "Unknown error")
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                        break
                        
            except Exception as e:
                # Send error response
                error_data = {
                    "status": "error",
                    "message": f"RAG query failed: {str(e)}"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ RAG query error: {str(e)}")
        print(f"❌ Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")

# Define the legacy chat endpoint that handles POST requests
@app.post("/api/legacy_chat")
async def legacy_chat(request: ChatRequest):
    try:
        # Initialize OpenAI client with the environment variable API key
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Create an async generator function for streaming responses
        async def generate():
            # Create a streaming chat completion request
            stream = client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "developer", "content": request.developer_message},
                    {"role": "user", "content": request.user_message}
                ],
                stream=True  # Enable streaming response
            )
            
            # Yield each chunk of the response as it becomes available
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        # Return a streaming response to the client
        return StreamingResponse(generate(), media_type="text/plain")
    
    except Exception as e:
        # Handle any errors that occur during processing
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Endpoint to upload a PDF file, save it to disk, and index it using aimakerspace.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    file_path = os.path.join(PDF_UPLOAD_DIR, file.filename)
    
    try:
        # Save the uploaded PDF
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Index the PDF using aimakerspace
        await index_pdf(file_path, file.filename)
        
        # Clean up temporary file (ephemeral processing)
        try:
            os.remove(file_path)
        except:
            pass  # Ignore cleanup errors
        
        return {
            "filename": file.filename, 
            "message": "PDF uploaded and indexed successfully (ephemeral).",
            "status": "indexed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        raise e

def simple_chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Simple text chunking function."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
    return [chunk for chunk in chunks if chunk]

async def index_pdf(file_path: str, filename: str):
    """
    Index a PDF file using simple text extraction and chunking.
    Note: This is a simplified version for demonstration.
    In production, you'd want to use the LangGraph RAG system for vectorization.
    """
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(file_path)
        
        # Create simple chunks
        chunks = simple_chunk_text(text, chunk_size=500, chunk_overlap=100)
        
        print(f"Created {len(chunks)} chunks from PDF: {filename}")
        
        # Store chunks in memory (simplified storage)
        pdf_vector_dbs[filename] = {
            'chunks': chunks,
            'text': text
        }
        
        print(f"Successfully indexed PDF: {filename} with {len(chunks)} chunks")
        
    except Exception as e:
        print(f"Error indexing PDF {filename}: {str(e)}")
        raise e

@app.post("/api/pdf_chat")
async def pdf_chat(request: PDFChatRequest):
    """
    Endpoint to chat with an uploaded PDF using RAG (Retrieval-Augmented Generation).
    """
    try:
        # Check if the PDF has been indexed
        if request.pdf_filename not in pdf_vector_dbs:
            raise HTTPException(
                status_code=404, 
                detail=f"PDF '{request.pdf_filename}' not found or not indexed. Please upload it first."
            )
        
        pdf_data = pdf_vector_dbs[request.pdf_filename]
        chunks = pdf_data['chunks']
        
        # Simple keyword search for relevant chunks (simplified approach)
        question_words = request.question.lower().split()
        relevant_chunks = []
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            if any(word in chunk_lower for word in question_words):
                relevant_chunks.append(chunk)
                if len(relevant_chunks) >= 3:
                    break
        
        # If no relevant chunks found, use first few chunks
        if not relevant_chunks:
            relevant_chunks = chunks[:3]
        
        # Combine relevant chunks into context
        context = "\n\n".join(relevant_chunks)
        
        # Create RAG prompt
        rag_prompt = f"""You are a helpful assistant that answers questions based on the provided context from a PDF document.

Context from the PDF:
{context}

Question: {request.question}

Please answer the question based on the context provided. If the context doesn't contain enough information to answer the question, say so. Keep your answer concise and relevant."""

        # Use OpenAI directly instead of aimakerspace wrapper
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "user", "content": rag_prompt}
            ]
        )
        
        return {
            "answer": response.choices[0].message.content,
            "pdf_filename": request.pdf_filename,
            "relevant_chunks_used": len(relevant_chunks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get("/api/test-rag")
async def test_rag():
    """Test RAG components individually."""
    results = {}
    
    # Test 1: Search function
    try:
        from langgraph_inspector_rag import _initialize_clients, search_inspector_standards
        # Force initialization
        _initialize_clients()
        search_results = search_inspector_standards("electrical clearance")
        results["search"] = {
            "status": "success",
            "count": len(search_results),
            "sample": search_results[0] if search_results else None
        }
    except Exception as e:
        results["search"] = {"status": "error", "error": str(e)[:200], "type": type(e).__name__}
    
    # Test 2: OpenAI connection
    try:
        import httpx
        from langchain_openai import ChatOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            results["openai"] = {"status": "error", "error": "No API key"}
        else:
            # Test with timeout and explicit client
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=api_key,
                temperature=0,
                request_timeout=10,
                max_retries=1
            )
            response = llm.invoke("Say 'test successful'")
            results["openai"] = {"status": "success", "response": response.content[:50]}
    except httpx.ConnectError as e:
        results["openai"] = {"status": "error", "error": "Network connection failed", "details": str(e)[:100]}
    except Exception as e:
        results["openai"] = {"status": "error", "error": str(e)[:200], "type": type(e).__name__}
    
    # Test 3: Direct API calls
    try:
        import requests
        # Test OpenAI directly
        headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
        results["openai_direct"] = {"status": response.status_code, "ok": response.ok}
    except Exception as e:
        results["openai_direct"] = {"status": "error", "error": str(e)[:100]}
    
    # Test 4: Direct Qdrant test
    try:
        import requests
        headers = {"api-key": os.getenv("QDRANT_API_KEY")}
        response = requests.get(f"{os.getenv('QDRANT_URL')}/collections", headers=headers, timeout=5)
        results["qdrant_direct"] = {"status": response.status_code, "ok": response.ok}
    except Exception as e:
        results["qdrant_direct"] = {"status": "error", "error": str(e)[:100]}
    
    return results

# Define a health check endpoint to verify API status
@app.get("/api/health")
async def health_check():
    # Test Qdrant connection
    qdrant_status = "unknown"
    qdrant_error = None
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        collections = client.get_collections()
        qdrant_status = f"connected ({len(collections.collections)} collections)"
    except Exception as e:
        qdrant_status = "error"
        qdrant_error = str(e)[:100]
    
    return {
        "status": "ok",
        "env_vars": {
            "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "not set",
            "QDRANT_URL": "set" if os.getenv("QDRANT_URL") else "not set", 
            "QDRANT_API_KEY": "set" if os.getenv("QDRANT_API_KEY") else "not set"
        },
        "env_lengths": {
            "OPENAI_KEY_LEN": len(os.getenv("OPENAI_API_KEY", "")),
            "QDRANT_URL_LEN": len(os.getenv("QDRANT_URL", "")),
            "QDRANT_KEY_LEN": len(os.getenv("QDRANT_API_KEY", ""))
        },
        "services": {
            "qdrant": qdrant_status,
            "qdrant_error": qdrant_error
        },
        "debug": {
            "total_env_vars": len(os.environ),
            "vercel_region": os.getenv("VERCEL_REGION", "unknown")
        }
    }

# Entry point for running the application directly
if __name__ == "__main__":
    import uvicorn
    # Start the server on all network interfaces (0.0.0.0) on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
