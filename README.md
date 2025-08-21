# House Whisperer – AI‑powered Home Inspection Assistant

## NC Home Inspector AI Assistant

A multi-agent RAG system that helps home buyers understand inspection reports by combining regulatory standards with real-time web information.

## 🎯 Problem Statement

Home buyers receive 30+ page technical inspection reports filled with jargon they don't understand, leading to confusion and poor decision-making during the largest purchase of their lives.

## 💡 Solution

An AI-powered chatbot that provides plain-English explanations of inspection findings by searching both:
- Pre-indexed NC inspection standards (InterNACHI, NCHILB, Building Codes)
- Real-time web search for recalls, manufacturers, and current best practices

## 🏗️ Architecture

### Multi-Agent System (LangGraph)
1. **Supervisor Agent** - Routes queries based on content analysis
2. **Research Agent** - Searches vector database (Qdrant)
3. **Web Search Agent** - Queries external sources (Tavily API)
4. **Synthesis Agent** - Generates comprehensive responses (GPT-4o-mini)

### Tech Stack
- **Frontend**: React + Tailwind CSS (Vercel)
- **Backend**: FastAPI + Python (Railway)
- **Vector DB**: Qdrant Cloud
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: text-embedding-3-small
- **Web Search**: Tavily API

## 🌐 Live Demo

The application is deployed and available at: https://house-whisperer.vercel.app/

## 🚀 If you want to run locally instead, 

### Prerequisites
- Node.js 18+
- Python 3.9+
- OpenAI API key
- Qdrant Cloud account
- Tavily API key

### 1. Clone the Repository
```bash
git clone https://github.com/rchallapilla/House_Whisperer.git
cd House_Whisperer
```

### 2. Backend Setup
```bash
cd api
pip install -r requirements.txt

# Create .env file with your credentials
cat > .env << EOF
OPENAI_API_KEY=your-openai-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-key
TAVILY_API_KEY=your-tavily-key
EOF

# Run the API server
python app.py
# API will be available at http://localhost:8000
```

### 3. Frontend Setup (in new terminal)
```bash
cd frontend
npm install

# Set API URL to local backend
echo "REACT_APP_API_URL=http://localhost:8000" > .env.development

# Start the React app
npm start
# App will open at http://localhost:3000
```

### 4. Test the Application
- Open http://localhost:3000 in your browser
- Try asking questions like:
  - "What are the electrical inspection requirements in NC?"
  - "Are there any recalls on Rheem water heaters?"
  - "How do I inspect HVAC systems?"

## 📊 Key Features

- **Intelligent Query Routing**: Automatically determines if web search is needed
- **Source Attribution**: Shows relevance scores and source types
- **Real-time Streaming**: SSE for progress updates during search
- **Fallback Strategies**: Web search when RAG returns no results

### Batch runner
- `scripts/run_batch_questions_chat_eval.py` supports `--print-config` to print masked backend config and embeds it into the run’s JSONL/Markdown outputs for traceability.

### Inspector RAG flow
- Default behavior: single pass — `RAG → optional Web → Synthesis`.
- Web augmentation can run once when RAG is empty, or when `USE_WEB_AUGMENT=1` and the query matches keywords.
- Implemented in `api/langgraph_inspector_rag.py` (nodes: `policy_node`, `rag_tool_node`, `web_tool_node`, `synthesis_node`).

## 🔍 Example Queries

- "What are the electrical inspection requirements in NC?"
- "Are there any recalls on Rheem water heaters?"
- "What's the latest on AFCI requirements?"
- "How do I inspect HVAC systems?"

## 📁 Project Structure

```
House_Whisperer/
├── api/
│   ├── app.py                    # FastAPI server
│   ├── langgraph_inspector_rag.py # Multi-agent workflow
│   └── web_search_tools.py       # Tavily integration
├── frontend/
│   └── src/
│       └── components/
│           └── ChatbotWidget.js  # Chat interface
└── docs/
    └── data/                     # Indexed documents
```

## 📚 Narratives Indexing, Mapping, and Testing (Qdrant)

Use this when enabling narrative suggestions in report generation. It maps narrative sections (from CSV) to canonical report sections (from YAML), builds a Qdrant collection, and sanity‑checks retrieval.

### Prereqs
- Env vars: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`
- Files: `docs/reference/narratives.csv`, `api/config/report_sections.yaml`

### 1) Generate mapping (narrative → report)
Produces `scripts/config/narratives_to_report_section_map.json` using exact/alias/token/semantic/fuzzy.

```bash
export OPENAI_API_KEY=YOUR_KEY
python scripts/generate_narratives_to_report_map.py \
  --csv docs/reference/narratives.csv \
  --yaml api/config/report_sections.yaml \
  --out scripts/config/narratives_to_report_section_map.json \
  --use-embeddings 1
```

If any entries are `UNMAPPED`, edit the JSON and set `report_section_key`. Demo defaults:
- `attic` → `insulation_ventilation`
- `homesite` → `site_drainage`
- `log_home` → `exterior`

### 2) Build Qdrant collection
Embeds narratives and normalizes `payload.section` to the report section key.

```bash
python scripts/build_narratives_index.py \
  --csv docs/reference/narratives.csv \
  --collection narratives_v1 \
  --dim 1536 \
  --batch-size 64 \
  --map scripts/config/narratives_to_report_section_map.json
```

### 3) Create payload indices (once)
If you see an error about `Index required for "section"`, create:

```bash
python -c "import os; from qdrant_client import QdrantClient; from qdrant_client.http.models import PayloadSchemaType as T; c=QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY']); c.create_payload_index('narratives_v1', field_name='section', field_schema=T.KEYWORD)"

# Optional audit indices
python -c "import os; from qdrant_client import QdrantClient; from qdrant_client.http.models import PayloadSchemaType as T; c=QdrantClient(url=os.environ['QDRANT_URL'], api_key=os.environ['QDRANT_API_KEY']); c.create_payload_index('narratives_v1', field_name='section_report', field_schema=T.KEYWORD); c.create_payload_index('narratives_v1', field_name='section_narrative', field_schema=T.KEYWORD)"
```

### 4) Test retrieval (10 cases)
```bash
python scripts/test/test_narratives_search.py --collection narratives_v1 --top-k 5
```
You’ll get PASS/FAIL per test and a summary. This mirrors production: embed transcript → filter by `payload.section == clip.section` → similarity search.

### Production usage
- Each clip has `clip.section` = report section key (YAML).
- Query Qdrant with filter `payload.section == clip.section`, rank by similarity to the transcript.
- Use top hits as suggested narratives; LLM writes the section summary separately.

### Demo-day narratives coverage (what to test now)
Based on current indexing and mappings, these report sections have narrative coverage and are good candidates for test cases:
- electrical, roof, insulation_ventilation (attic insulation/ventilation), plumbing, hvac, interior, garage, exterior, structure, kitchen, pools_spas, environmental, site_drainage (sparse but present)

Sections currently lacking mapped narratives (skip for now unless we add conditional duplication/mappings):
- bathrooms, fireplaces_chimneys, laundry, summary (summary is synthesized, not narrative-driven)

Notes:
- `attic` narratives are mapped to the report section `insulation_ventilation`.
- If you need fireplaces/chimneys, add mappings for narrative sections mentioning fireplace/chimney/flue to `fireplaces_chimneys` and rebuild the index.

## 🧾 Report Generation (current)

- Media capture: audio + photos per clip; automatic Whisper transcription.
- Persistent data: Firestore (inspections, clips, transcripts), Firebase Storage (media).
- Report writer (Option B2): structured outline → per‑section LLM summary (gpt‑4o‑mini) → observations (transcript first sentence + suggested narratives + photos) → Markdown draft stored under `inspections/{id}/reports/draft`.
- Narratives: indexed to Qdrant; queries filter by `payload.section == clip.section` and rank by similarity to the transcript.
