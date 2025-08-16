# House Whisperer API (FastAPI)

Streaming inspector RAG and utilities for the House Whisperer app. Built with FastAPI, LangGraph, Qdrant, Tavily, and OpenAI.

## Quick start

1) Create a virtual environment
```bash
cd api
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```

2) Install dependencies
```bash
pip install -r requirements.txt
```

3) Configure environment
Create `api/.env` and set at least:
```
OPENAI_API_KEY=...
QDRANT_URL=...
QDRANT_API_KEY=...
TAVILY_API_KEY=...
# Optional web augmentation knobs
USE_WEB_AUGMENT=0
WEB_AUGMENT_KEYWORDS=recall,manufacturer,cpsc,best practices,how to,current,update,installation manual,model,serial,2024
WEB_TOOL_FETCH_LIMIT=8
WEB_AUGMENT_MAX=5
WEB_MIN_SCORE_GENERIC=0.4
WEB_MIN_SCORE_RECALL=0.3
```

4) Run locally
```bash
# from repo root
uvicorn app:app --reload --port 8000 --app-dir api
# or from api/
python app.py
```

## Endpoints

### POST `/api/chat` (SSE streaming)
Agentic Inspector RAG over Qdrant with optional one-pass web augmentation.

Request body
```json
{ "message": "What are the continuing education requirements?", "sessionId": "local" }
```

Response (Server-Sent Events)
- status: starting/progress/response_start/response_chunk/sources/complete
- Chunks stream incrementally; client should concatenate `response_chunk` values.

Minimal curl (prints events):
```bash
curl -N -H "Content-Type: application/json" \
  -d '{"message":"What are NC inspector CE requirements?","sessionId":"local"}' \
  http://localhost:8000/api/chat
```

### POST `/api/legacy_chat`
Direct OpenAI streaming using developer/user messages. Kept for reference.

### GET `/api/config`
Returns the effective runtime configuration with secrets masked.

### GET `/api/test-rag`
Connectivity and sanity checks (env lengths, sample search, OpenAI/Qdrant probes).

### GET `/api/health`
Basic health plus Qdrant connectivity status.

### PDF (demo endpoints)
- `POST /api/upload_pdf` — upload and index a PDF into an in-memory demo store
- `POST /api/pdf_chat` — simple RAG over the uploaded PDF demo store

## How Inspector RAG works (short)
- LangGraph pipeline: `policy` → `rag_tool` → conditional `web_tool` → `synthesis` → END
- Retrieval: Qdrant collection `inspector-standards-postmidterm` (threshold 0.55, diversified sources)
- Web augmentation: one pass when `USE_WEB_AUGMENT=1` and query matches `WEB_AUGMENT_KEYWORDS`, or when RAG returns no context
- Synthesis: clearly separates regulatory sources and web resources

See `docs/ARCHITECTURE.md` for the diagrams.

## CORS
Origins are taken from `ALLOWED_ORIGINS` and `VERCEL_URL` (when present). Update env rather than code for deployments.

## Troubleshooting
- No output from chat: check server logs; verify `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, and network access
- Web results always empty: ensure `TAVILY_API_KEY`; check logs for filter summaries; consider lowering `WEB_MIN_SCORE_GENERIC`
- CORS errors: set correct frontend origin(s) in `ALLOWED_ORIGINS`

## License
Internal course/demo project.