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
from uuid import uuid4
import asyncio
import httpx
import json as _json
import yaml
from functools import lru_cache

# Optional: Firebase Admin to persist transcripts to Firestore
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as admin_firestore
    _FIREBASE_AVAILABLE = True
except Exception:
    _FIREBASE_AVAILABLE = False

# Load environment variables for local development from api/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=False)

# Standard imports for PDF processing and text handling
import PyPDF2
from io import BytesIO
import markdown
import weasyprint
from datetime import datetime

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

# ---- Effective config snapshot (masked) ----
def _mask_secret(value: Optional[str], head: int = 4, tail: int = 2) -> str:
    """Mask secrets for safe logging/return. Shows head and tail with length."""
    if not value:
        return "not set"
    value = str(value)
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}...{value[-tail:]} (len={len(value)})"

def get_effective_backend_config() -> dict:
    """Return effective backend config/environment (secrets masked)."""
    def csv_list(var_name: str, default: str = ""):
        raw = os.getenv(var_name, default)
        items = [s.strip() for s in raw.split(",") if s.strip()]
        return items

    cfg = {
        # Secrets masked
        "OPENAI_API_KEY": _mask_secret(os.getenv("OPENAI_API_KEY")),
        "QDRANT_API_KEY": _mask_secret(os.getenv("QDRANT_API_KEY")),
        "TAVILY_API_KEY": _mask_secret(os.getenv("TAVILY_API_KEY")),

        # Non-secrets
        "QDRANT_URL": os.getenv("QDRANT_URL", ""),
        "ALLOWED_ORIGINS": ALLOWED_ORIGINS,
        # Policy loop removed from active code; flags omitted
        "USE_WEB_AUGMENT": os.getenv("USE_WEB_AUGMENT", "0"),
        "WEB_AUGMENT_KEYWORDS": csv_list("WEB_AUGMENT_KEYWORDS"),
        "WEB_TOOL_FETCH_LIMIT": int(os.getenv("WEB_TOOL_FETCH_LIMIT", "8") or 8),
        "WEB_AUGMENT_MAX": int(os.getenv("WEB_AUGMENT_MAX", "5") or 5),
        "WEB_MIN_SCORE_GENERIC": float(os.getenv("WEB_MIN_SCORE_GENERIC", "0.4") or 0.4),
        "WEB_MIN_SCORE_RECALL": float(os.getenv("WEB_MIN_SCORE_RECALL", "0.3") or 0.3),
        "VERCEL_URL": os.getenv("VERCEL_URL"),
        "VERCEL_REGION": os.getenv("VERCEL_REGION"),
        "PORT": os.getenv("PORT", "8000"),
    }
    return cfg

try:
    print("🔧 Effective backend config (masked secrets):")
    print(json.dumps(get_effective_backend_config(), indent=2))
except Exception as _cfg_err:
    print(f"⚠️ Could not print effective config: {_cfg_err}")

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
admin_db = None  # Firestore admin client (set on startup if available)
_ADMIN_WARN_SHOWN = False

# -------------------------
# In-memory POC storage for Inspections & Clips (Phase 1)
# -------------------------
class CreateInspectionRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class Inspection(BaseModel):
    id: str
    name: Optional[str] = None
    address: Optional[str] = None


class CreateClipRequest(BaseModel):
    audio_url: str
    photos: Optional[list[dict]] = None  # [{id,url,user_caption?}]
    notes: Optional[str] = None
    clip_id: Optional[str] = None


class Clip(BaseModel):
    id: str
    inspection_id: str
    audio_url: str
    photos: list[dict]
    notes: Optional[str] = None
    status: str = "queued"  # queued | processing | done | error
    transcript: Optional[str] = None
    error: Optional[str] = None


_INSPECTIONS: dict[str, Inspection] = {}
_CLIPS: dict[str, Clip] = {}

# Simple async queue for auto-transcription
_TRANSCRIBE_QUEUE: asyncio.Queue[str] = asyncio.Queue()

USE_AUTO_TRANSCRIBE = os.getenv("USE_AUTO_TRANSCRIBE", "1") == "1"

# Backend timeouts (allow >= 2-minute clips comfortably)
DOWNLOAD_TIMEOUT_SEC = int(os.getenv("AUDIO_DOWNLOAD_TIMEOUT_SEC", "300") or 300)
WHISPER_TIMEOUT_SEC = int(os.getenv("WHISPER_TIMEOUT_SEC", "300") or 300)


async def _refresh_inspection_status(inspection_id: str):
    """Recompute inspection status in Firestore based on clip statuses."""
    try:
        if not admin_db:
            return
        clips_ref = admin_db.collection("inspections").document(inspection_id).collection("clips")
        clips = list(clips_ref.stream())
        total = 0
        done = 0
        error = 0
        queued = 0
        processing = 0
        for d in clips:
            data = d.to_dict() or {}
            # Ignore placeholder docs that do not have an audio URL
            if not (data.get("audioUrl") or data.get("audio_url")):
                continue
            total += 1
            st = data.get("status")
            if st == "done":
                done += 1
            elif st == "error":
                error += 1
            elif st == "processing":
                processing += 1
            else:
                queued += 1
        if total == 0:
            status = "empty"
        elif done == total:
            status = "done"
        elif error > 0:
            status = "attention"
        else:
            status = "in_progress"
        admin_db.collection("inspections").document(inspection_id).set({
            "status": status,
            "counts": {
                "total": total,
                "done": done,
                "error": error,
                "queued": queued,
                "processing": processing,
            }
        }, merge=True)
    except Exception as e:
        print(f"⚠️ Failed to refresh inspection status: {e}")


async def _scan_and_enqueue_queued_from_firestore():
    """On startup, re-enqueue any clips stuck in queued/processing in Firestore.
    This ensures resilience across backend restarts.
    """
    if not admin_db:
        return
    try:
        q = admin_db.collection_group("clips").where("status", "in", ["queued", "processing"])  # type: ignore[arg-type]
        docs = list(q.stream())
        to_enqueue: list[str] = []
        for d in docs:
            data = d.to_dict() or {}
            clip_id = d.id
            inspection_ref = d.reference.parent.parent
            inspection_id = inspection_ref.id if inspection_ref else data.get("inspectionId")
            audio_url = data.get("audioUrl") or data.get("audio_url")
            photos = data.get("photos") or []
            notes = data.get("notes") or None
            if not inspection_id or not audio_url:
                print(f"⚠️ Skipping clip {clip_id}: missing inspection_id or audio_url")
                continue
            if clip_id not in _CLIPS:
                _CLIPS[clip_id] = Clip(
                    id=clip_id,
                    inspection_id=inspection_id,
                    audio_url=audio_url,
                    photos=photos,
                    notes=notes,
                    status="queued",
                )
            to_enqueue.append(clip_id)
        if to_enqueue:
            print(f"🔁 Re-enqueuing {len(to_enqueue)} clip(s) from Firestore (queued/processing): {to_enqueue}")
            for cid in to_enqueue:
                await _TRANSCRIBE_QUEUE.put(cid)
        else:
            print("🔁 No queued/processing clips found to re-enqueue")
    except Exception as e:
        print(f"⚠️ Startup re-enqueue scan failed: {e}")


async def _enqueue_specific_clip(clip_id: str) -> bool:
    if not admin_db:
        return False
    try:
        # Scan collection group for the specific clip document id
        docs = list(admin_db.collection_group("clips").stream())
        for d in docs:
            if d.id != clip_id:
                continue
            data = d.to_dict() or {}
            inspection_ref = d.reference.parent.parent
            inspection_id = inspection_ref.id if inspection_ref else data.get("inspectionId")
            audio_url = data.get("audioUrl") or data.get("audio_url")
            photos = data.get("photos") or []
            notes = data.get("notes") or None
            if not inspection_id or not audio_url:
                print(f"⚠️ Cannot enqueue {clip_id}: missing inspection_id or audio_url")
                return False
            _CLIPS[clip_id] = Clip(
                id=clip_id,
                inspection_id=inspection_id,
                audio_url=audio_url,
                photos=photos,
                notes=notes,
                status="queued",
            )
            await _TRANSCRIBE_QUEUE.put(clip_id)
            print(f"➡️ Enqueued specific clip {clip_id} for transcription")
            return True
        print(f"⚠️ Clip {clip_id} not found in Firestore collection group")
        return False
    except Exception as e:
        print(f"⚠️ enqueue_specific_clip failed: {e}")
        return False


async def _recompute_all_inspection_counts():
    if not admin_db:
        return
    try:
        docs = list(admin_db.collection("inspections").stream())
        for d in docs:
            await _refresh_inspection_status(d.id)
        print(f"🧮 Recomputed counts/status for {len(docs)} inspection(s)")
    except Exception as e:
        print(f"⚠️ Recompute-all failed: {e}")


async def _worker_transcribe_loop():
    """Background worker that downloads clip audio and runs transcription."""
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=WHISPER_TIMEOUT_SEC)
    while True:
        clip_id = await _TRANSCRIBE_QUEUE.get()
        try:
            clip = _CLIPS.get(clip_id)
            if not clip:
                print(f"⚠️ Worker received unknown clip_id {clip_id}; skipping")
                _TRANSCRIBE_QUEUE.task_done()
                continue
            print(f"🎧 Processing clip {clip.id} (inspection {clip.inspection_id})")
            clip.status = "processing"
            # Firestore: mark processing
            try:
                if admin_db and clip.inspection_id:
                    admin_db.collection("inspections").document(clip.inspection_id).collection("clips").document(clip.id).set({
                        "status": "processing"
                    }, merge=True)
            except Exception as e:
                print(f"⚠️ Firestore update (processing) failed: {e}")

            # Download audio bytes
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT_SEC) as aclient:
                resp = await aclient.get(clip.audio_url)
                resp.raise_for_status()
                audio_bytes = resp.content

            buf = BytesIO(audio_bytes)
            buf.name = "audio.m4a"

            # Transcribe via Whisper
            try:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=buf,
                    response_format="text",
                )
                transcript_text = result if isinstance(result, str) else getattr(result, "text", None) or str(result)
            except Exception as e:  # fallback to chat if needed
                print(f"⚠️ Whisper error for clip {clip.id}: {e}")
                transcript_text = f"[transcription_error:{e}]"

            clip.transcript = transcript_text
            clip.status = "done"
            try:
                if admin_db and clip.inspection_id:
                    admin_db.collection("inspections").document(clip.inspection_id).collection("clips").document(clip.id).set({
                        "status": "done",
                        "transcript": transcript_text
                    }, merge=True)
                    await _refresh_inspection_status(clip.inspection_id)
            except Exception as e:
                print(f"⚠️ Firestore update (done) failed: {e}")
            print(f"✅ Finished clip {clip.id}")
        except Exception as e:
            clip = _CLIPS.get(clip_id)
            if clip:
                clip.status = "error"
                clip.error = str(e)[:500]
                try:
                    if admin_db and clip.inspection_id:
                        admin_db.collection("inspections").document(clip.inspection_id).collection("clips").document(clip.id).set({
                            "status": "error",
                            "error": clip.error
                        }, merge=True)
                        await _refresh_inspection_status(clip.inspection_id)
                except Exception as e2:
                    print(f"⚠️ Firestore update (error) failed: {e2}")
            print(f"❌ Worker failed on clip {clip_id}: {e}")
        finally:
            _TRANSCRIBE_QUEUE.task_done()


@app.on_event("startup")
async def _startup_background_workers():
    if USE_AUTO_TRANSCRIBE:
        # Initialize Firebase Admin if possible (for Firestore updates)
        global admin_db
        if _FIREBASE_AVAILABLE and not getattr(firebase_admin, "_apps", []):
            svc_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            if svc_json:
                try:
                    cred = credentials.Certificate(_json.loads(svc_json))
                    firebase_admin.initialize_app(cred)
                    admin_db = admin_firestore.client()
                    print("✅ Firebase Admin initialized for Firestore updates")
                except Exception as e:
                    print(f"⚠️ Firebase Admin init failed: {e}")
            else:
                print("❌ FIREBASE_SERVICE_ACCOUNT_JSON not set; Firestore updates DISABLED (set this in api/.env)")
        elif _FIREBASE_AVAILABLE and getattr(firebase_admin, "_apps", []):
            admin_db = admin_firestore.client()
        else:
            print("❌ firebase_admin library not available; install firebase-admin or disable Firestore updates")
        if not admin_db:
            print("❌ Firebase Admin NOT initialized. Transcripts will NOT be written to Firestore; UI will not update in real time.")
        # Start worker and re-enqueue any pending clips
        asyncio.create_task(_worker_transcribe_loop())
        await _scan_and_enqueue_queued_from_firestore()
        # Backfill counts/status so the list has accurate totals immediately
        await _recompute_all_inspection_counts()

# Manual endpoint to recompute counts/status if needed
@app.post("/api/admin/recompute_counts")
async def recompute_counts_admin():
    if not admin_db:
        raise HTTPException(status_code=400, detail="Firebase Admin not initialized")
    await _recompute_all_inspection_counts()
    return {"ok": True}

@app.post("/api/admin/requeue_queued")
async def requeue_queued_admin():
    if not admin_db:
        raise HTTPException(status_code=400, detail="Firebase Admin not initialized")
    await _scan_and_enqueue_queued_from_firestore()
    return {"ok": True}

@app.post("/api/admin/requeue_clip/{clip_id}")
async def requeue_clip_admin(clip_id: str):
    if not admin_db:
        raise HTTPException(status_code=400, detail="Firebase Admin not initialized")
    ok = await _enqueue_specific_clip(clip_id)
    return {"ok": ok}

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
    
    # Test 0: Environment variables
    results["env_check"] = {
        "OPENAI_KEY": f"{len(os.getenv('OPENAI_API_KEY', ''))} chars, ends with: {repr(os.getenv('OPENAI_API_KEY', '')[-5:])}",
        "QDRANT_URL": f"{len(os.getenv('QDRANT_URL', ''))} chars, ends with: {repr(os.getenv('QDRANT_URL', '')[-5:])}",
        "QDRANT_KEY": f"{len(os.getenv('QDRANT_API_KEY', ''))} chars, ends with: {repr(os.getenv('QDRANT_API_KEY', '')[-5:])}"
    }
    
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
        # Test OpenAI directly (strip whitespace)
        api_key = os.getenv('OPENAI_API_KEY', '').strip()
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
        results["openai_direct"] = {"status": response.status_code, "ok": response.ok}
    except Exception as e:
        results["openai_direct"] = {"status": "error", "error": str(e)[:100]}
    
    # Test 4: Direct Qdrant test
    try:
        import requests
        # Strip whitespace from both URL and API key
        qdrant_url = os.getenv('QDRANT_URL', '').strip()
        qdrant_key = os.getenv('QDRANT_API_KEY', '').strip()
        headers = {"api-key": qdrant_key}
        response = requests.get(f"{qdrant_url}/collections", headers=headers, timeout=5)
        results["qdrant_direct"] = {"status": response.status_code, "ok": response.ok}
    except Exception as e:
        results["qdrant_direct"] = {"status": "error", "error": str(e)[:100]}
    
    return results

# Safe config endpoint (masked)
@app.get("/api/config")
async def get_config():
    try:
        return {"config": get_effective_backend_config()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config error: {str(e)}")

# Define a health check endpoint to verify API status
@app.get("/api/health")
async def health_check():
    # Test Qdrant connection
    qdrant_status = "unknown"
    qdrant_error = None
    try:
        from qdrant_client import QdrantClient
        # Strip whitespace from environment variables
        qdrant_url = os.getenv("QDRANT_URL", "").strip()
        qdrant_key = os.getenv("QDRANT_API_KEY", "").strip()
        client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_key
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
            "QDRANT_KEY_LEN": len(os.getenv("QDRANT_API_KEY", "")),
            "QDRANT_URL_LAST": repr(os.getenv("QDRANT_URL", "")[-5:]) if os.getenv("QDRANT_URL") else "none",
            "QDRANT_KEY_LAST": os.getenv("QDRANT_API_KEY", "")[-10:] if os.getenv("QDRANT_API_KEY") else "none"
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

@lru_cache(maxsize=1)
def _load_report_sections() -> list:
    try:
      	# Prefer local YAML shipped inside api/ for serverless/monorepo deployments
        base_api = os.path.dirname(__file__)
        env_path = os.getenv('REPORT_SECTIONS_PATH')
        if env_path and os.path.exists(env_path):
            yaml_path = env_path
        else:
            preferred_yaml = os.path.join(base_api, 'config', 'report_sections.yaml')
            legacy_local = os.path.join(base_api, 'report_sections.yaml')
            if os.path.exists(preferred_yaml):
                yaml_path = preferred_yaml
            elif os.path.exists(legacy_local):
                yaml_path = legacy_local
            else:
                raise FileNotFoundError("report_sections.yaml not found; expected at api/config/report_sections.yaml or set REPORT_SECTIONS_PATH")
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        sections = data.get('sections') or []
        out = []
        for s in sections:
            key = (s.get('key') or '').strip()
            label = (s.get('label') or key).strip()
            includes = s.get('includes') or []
            inc = [str(x) for x in includes if isinstance(x, (str, int, float))]
            if key:
                out.append({'key': key, 'label': label, 'includes': inc})
        # Attach required list if present
        required = data.get('required_sections') or []
        return {'sections': out, 'required_sections': required}
    except Exception as e:
        print(f"⚠️ Failed to load report sections YAML: {e}")
        return []


@app.get('/api/report_sections')
async def get_report_sections():
    data = _load_report_sections()
    # Backward compatibility: if older cache structure, wrap
    if isinstance(data, list):
        return {'sections': data, 'required_sections': []}
    return data

# -------------------------
# Inspection & Clips API (POC)
# -------------------------


@app.post("/api/inspections")
async def create_inspection(req: CreateInspectionRequest):
    insp_id = str(uuid4())
    insp = Inspection(id=insp_id, name=req.name, address=req.address)
    _INSPECTIONS[insp_id] = insp
    # Persist to Firestore if available so IDs survive restarts
    try:
        if admin_db:
            admin_db.collection("inspections").document(insp_id).set({
                "name": req.name,
                "address": req.address,
                "status": "in_progress",
                "createdAt": admin_firestore.SERVER_TIMESTAMP,
            }, merge=True)
    except Exception as e:
        print(f"⚠️ Firestore write (create_inspection) failed: {e}")
    return insp.model_dump()


@app.get("/api/inspections")
async def list_inspections():
    # Prefer Firestore when available
    if admin_db:
        try:
            docs = list(admin_db.collection("inspections").stream())
            items = []
            for d in docs:
                data = d.to_dict() or {}
                # Live count clips for this inspection (only those with audioUrl)
                counts = {"total": 0, "done": 0, "error": 0, "queued": 0, "processing": 0}
                try:
                    clip_docs = list(admin_db.collection("inspections").document(d.id).collection("clips").stream())
                    for cd in clip_docs:
                        clip_data = cd.to_dict() or {}
                        audio_present = clip_data.get("audioUrl") or clip_data.get("audio_url")
                        if not audio_present:
                            continue  # skip placeholder docs
                        counts["total"] += 1
                        st = clip_data.get("status")
                        if st in counts:
                            counts[st] += 1
                except Exception as e:
                    print(f"⚠️ Could not count clips for {d.id}: {e}")
                # Derive status
                if counts["total"] == 0:
                    status = data.get("status") or "in_progress"
                elif counts["done"] == counts["total"]:
                    status = "done"
                elif counts["error"] > 0:
                    status = "attention"
                else:
                    status = "in_progress"
                items.append({
                    "id": d.id,
                    "name": data.get("name"),
                    "address": data.get("address"),
                    "status": status,
                    "counts": counts,
                })
            return {"inspections": items}
        except Exception as e:
            print(f"⚠️ Firestore list failed, falling back to in-memory: {e}")
    # Fallback to in-memory POC
    global _ADMIN_WARN_SHOWN
    if not _ADMIN_WARN_SHOWN:
        print("ℹ️ Listing inspections from in-memory store (Firestore admin not initialized)")
        _ADMIN_WARN_SHOWN = True
    items = []
    for insp in _INSPECTIONS.values():
        clips = [c for c in _CLIPS.values() if c.inspection_id == insp.id]
        counts = {
            "total": len([c for c in clips if c.audio_url]),
            "queued": sum(1 for c in clips if c.status == "queued"),
            "processing": sum(1 for c in clips if c.status == "processing"),
            "done": sum(1 for c in clips if c.status == "done"),
            "error": sum(1 for c in clips if c.status == "error"),
        }
        if counts["total"] == 0:
            status = "empty"
        elif counts["done"] == counts["total"]:
            status = "done"
        elif counts["error"] > 0:
            status = "attention"
        else:
            status = "in_progress"
        items.append({
            "id": insp.id,
            "name": insp.name,
            "status": status,
            "counts": counts,
        })
    return {"inspections": items}


@app.get("/api/inspections/{inspection_id}")
async def get_inspection(inspection_id: str):
    insp = _INSPECTIONS.get(inspection_id)
    if not insp:
        raise HTTPException(status_code=404, detail="inspection not found")
    clips = [c.model_dump() for c in _CLIPS.values() if c.inspection_id == inspection_id]
    return {"inspection": insp.model_dump(), "clips": clips}


@app.post("/api/inspections/{inspection_id}/clips")
async def create_clip(inspection_id: str, req: CreateClipRequest):
    # Validate inspection existence in Firestore (preferred) or accept if missing to avoid restart issues
    try:
        if admin_db:
            doc_ref = admin_db.collection("inspections").document(inspection_id)
            if not doc_ref.get().exists:
                # Create a minimal inspection doc so downstream writes are consistent
                doc_ref.set({
                    "status": "in_progress",
                    "createdAt": admin_firestore.SERVER_TIMESTAMP,
                }, merge=True)
    except Exception as e:
        print(f"⚠️ Firestore inspection check failed: {e}")
    if not req.audio_url:
        raise HTTPException(status_code=400, detail="audio_url is required")
    global _ADMIN_WARN_SHOWN
    if not admin_db and not _ADMIN_WARN_SHOWN:
        print("❌ Firebase Admin NOT initialized — will NOT persist status/transcripts to Firestore. Set FIREBASE_SERVICE_ACCOUNT_JSON in api/.env.")
        _ADMIN_WARN_SHOWN = True
    clip_id = req.clip_id or str(uuid4())
    clip = Clip(
        id=clip_id,
        inspection_id=inspection_id,
        audio_url=req.audio_url,
        photos=req.photos or [],
        notes=req.notes or None,
    )
    _CLIPS[clip_id] = clip
    if USE_AUTO_TRANSCRIBE:
        await _TRANSCRIBE_QUEUE.put(clip_id)
    # Refresh parent inspection status/counts so the list reflects queued clip counts immediately
    try:
        if admin_db:
            await _refresh_inspection_status(inspection_id)
    except Exception as e:
        print(f"⚠️ Refresh after clip create failed: {e}")
    return clip.model_dump()


@app.get("/api/clips/{clip_id}")
async def get_clip(clip_id: str):
    clip = _CLIPS.get(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")
    return clip.model_dump()


@app.delete("/api/clips/{clip_id}")
async def delete_clip(clip_id: str):
    clip = _CLIPS.pop(clip_id, None)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")
    return {"deleted": True, "clip_id": clip_id}


# -------- Report generation (Session 10 style LangGraph) --------
class GenerateReportRequest(BaseModel):
    inspectionId: str
    sections: Optional[list[str]] = None
    save: Optional[bool] = True


@app.post("/api/generate_report")
async def generate_report(req: GenerateReportRequest):
    if not req.inspectionId:
        raise HTTPException(status_code=400, detail="inspectionId is required")
    # Import runner with flexibility for both package and script modes
    try:
        from .langgraph_report_writer import run_report  # type: ignore
    except Exception:
        try:
            from api.langgraph_report_writer import run_report  # type: ignore
        except Exception:
            try:
                from langgraph_report_writer import run_report  # type: ignore
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Report graph unavailable: {e}")
    try:
        result = run_report(req.inspectionId, req.sections or [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")
    if not result.get("markdown"):
        raise HTTPException(status_code=400, detail="No content generated (ensure clips exist and sections match)")
    return {"ok": True, "saved": bool(result.get("saved")), "report": result}


class PublishReportRequest(BaseModel):
    inspectionId: str
    title: Optional[str] = None

class GeneratePDFRequest(BaseModel):
    inspectionId: str


@app.post("/api/publish_report")
async def publish_report(req: PublishReportRequest):
    if not req.inspectionId:
        raise HTTPException(status_code=400, detail="inspectionId is required")
    if not admin_db:
        raise HTTPException(status_code=500, detail="Firestore admin not initialized")
    try:
        draft_ref = admin_db.collection('inspections').document(req.inspectionId).collection('reports').document('draft')
        d = draft_ref.get()
        if not d.exists:
            raise HTTPException(status_code=400, detail="No draft report found")
        data = d.to_dict() or {}
        markdown = data.get('markdown')
        if not markdown:
            raise HTTPException(status_code=400, detail="Draft has no markdown")
        pub_ref = admin_db.collection('inspections').document(req.inspectionId).collection('reports').document()
        pub_data = {
            'markdown': markdown,
            'publishedAt': admin_firestore.SERVER_TIMESTAMP,
            'title': req.title or 'Published Report',
            'source': 'draft',
        }
        pub_ref.set(pub_data, merge=True)
        return {"ok": True, "publishedId": pub_ref.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish failed: {e}")


@app.delete("/api/inspections/{inspection_id}")
async def delete_inspection(inspection_id: str):
    """Delete an entire inspection and all its clips/reports"""
    if not admin_db:
        raise HTTPException(status_code=500, detail="Firestore admin not initialized")
    
    try:
        # Delete all clips in the inspection
        clips_ref = admin_db.collection('inspections').document(inspection_id).collection('clips')
        clips = list(clips_ref.stream())
        for clip_doc in clips:
            clip_doc.reference.delete()
        
        # Delete all reports in the inspection  
        reports_ref = admin_db.collection('inspections').document(inspection_id).collection('reports')
        reports = list(reports_ref.stream())
        for report_doc in reports:
            report_doc.reference.delete()
            
        # Delete the inspection document itself
        admin_db.collection('inspections').document(inspection_id).delete()
        
        # Also remove from in-memory storage if present
        if inspection_id in _INSPECTIONS:
            del _INSPECTIONS[inspection_id]
            
        return {"ok": True, "deleted": inspection_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete inspection: {e}")


@app.get("/api/debug_inspection/{inspection_id}")
async def debug_inspection(inspection_id: str):
    """Debug endpoint to check inspection data"""
    if not admin_db:
        return {"error": "Firestore not initialized"}
    
    try:
        # Get inspection metadata
        insp_doc = admin_db.collection('inspections').document(inspection_id).get()
        inspection_data = insp_doc.to_dict() if insp_doc.exists else {}
        
        # Get clips count
        clips = list(admin_db.collection('inspections').document(inspection_id).collection('clips').stream())
        clips_data = [{'id': c.id, 'data': c.to_dict()} for c in clips[:3]]  # First 3 clips
        
        return {
            "inspection_exists": insp_doc.exists,
            "inspection_data": inspection_data,
            "clips_count": len(clips),
            "sample_clips": clips_data
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/generate_pdf")
async def generate_pdf(req: GeneratePDFRequest):
    """Generate a PDF from the draft report markdown"""
    if not _PDF_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF generation not available on this deployment")
    if not req.inspectionId:
        raise HTTPException(status_code=400, detail="inspectionId is required")
    if not admin_db:
        raise HTTPException(status_code=500, detail="Firestore admin not initialized")
    
    try:
        # Get the draft report
        draft_ref = admin_db.collection('inspections').document(req.inspectionId).collection('reports').document('draft')
        d = draft_ref.get()
        if not d.exists:
            raise HTTPException(status_code=400, detail="No draft report found")
        
        data = d.to_dict() or {}
        markdown_content = data.get('markdown')
        if not markdown_content:
            raise HTTPException(status_code=400, detail="Draft has no markdown content")
        
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
        
        # Create a complete HTML document with CSS styling
        html_document = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Home Inspection Report</title>
            <style>
                @page {{
                    size: A4;
                    margin: 0.75in;
                }}
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    font-size: 11pt;
                }}
                h1 {{
                    color: #1f2937;
                    font-size: 24pt;
                    margin-bottom: 0.5em;
                    border-bottom: 2px solid #3b82f6;
                    padding-bottom: 0.2em;
                }}
                h2 {{
                    color: #374151;
                    font-size: 16pt;
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                    border-bottom: 1px solid #d1d5db;
                    padding-bottom: 0.1em;
                }}
                h3 {{
                    color: #4b5563;
                    font-size: 13pt;
                    margin-top: 1em;
                    margin-bottom: 0.3em;
                }}
                p {{
                    margin-bottom: 0.8em;
                }}
                ul, ol {{
                    margin-bottom: 0.8em;
                    padding-left: 1.2em;
                }}
                li {{
                    margin-bottom: 0.3em;
                }}
                strong {{
                    color: #1f2937;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 1em 0;
                    page-break-inside: avoid;
                }}
                figure {{
                    margin: 1em 0;
                    page-break-inside: avoid;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                    page-break-inside: avoid;
                }}
                th, td {{
                    border: 1px solid #d1d5db;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f3f4f6;
                    font-weight: 600;
                }}
                .report-header {{
                    text-align: center;
                    margin-bottom: 2em;
                    border-bottom: 3px solid #3b82f6;
                    padding-bottom: 1em;
                }}
                .inspection-details {{
                    background-color: #f9fafb;
                    padding: 1em;
                    border-radius: 4px;
                    margin-bottom: 1.5em;
                }}
                
                /* Page break handling */
                h2 {{
                    page-break-after: avoid;
                }}
                h3 {{
                    page-break-after: avoid;
                }}
                
                /* Ensure content doesn't break awkwardly */
                p, li {{
                    orphans: 2;
                    widows: 2;
                }}
                
                /* Image sizing for different screen sizes */
                @media print {{
                    img {{
                        max-height: 6in;
                        object-fit: contain;
                    }}
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF using WeasyPrint
        pdf_bytes = weasyprint.HTML(string=html_document).write_pdf()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inspection_report_{req.inspectionId[:8]}_{timestamp}.pdf"
        
        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# Entry point for running the application directly
if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment (Railway sets this) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
