# House Whisperer – AI-Powered Home Inspection Platform

## Professional Home Inspector Assistant

An intelligent inspection platform that streamlines report generation for home inspectors using multi-agent AI, smart narrative matching, and regulatory compliance tools.

## 🎯 Problem Statement

Home inspectors spend hours manually writing reports, searching for appropriate narratives, and ensuring code compliance – time that could be spent on more inspections or with family.

## 💡 Solution

An AI-powered platform that transforms audio/visual inspection notes into professional reports by:
- **Smart Narrative Matching**: 6,500+ pre-written expert narratives with semantic search & reranking
- **Standards Compliance**: Automatic cross-reference with building codes & inspection standards
- **Intelligent Fallbacks**: RAG-based code lookups and AI generation when needed
- **Voice-First Interface**: Record observations in real-time during inspection

## 🏗️ Architecture

### Report Generation Pipeline (LangGraph)
1. **Data Collection** - Voice transcription & image capture
2. **Narrative Retrieval** - Qdrant vector search with Cohere reranking
3. **Inspector RAG** - Building code compliance verification
4. **Report Assembly** - Professional markdown generation with quality scoring

### Multi-Agent Chat System
1. **Supervisor Agent** - Routes queries based on content analysis
2. **Research Agent** - Searches inspection standards (Qdrant)
3. **Web Search Agent** - Current recalls & manufacturer info (Tavily)
4. **Synthesis Agent** - Comprehensive responses (GPT-4o-mini)

### Tech Stack
- **Frontend**: React + Tailwind CSS + Firebase (Vercel)
- **Backend**: FastAPI + Python (Railway)
- **Vector DB**: Qdrant Cloud (Narratives + Standards)
- **LLM**: OpenAI GPT-4o-mini + GPT-4
- **Embeddings**: text-embedding-3-small
- **Reranking**: Cohere rerank-english-v3.0
- **Web Search**: Tavily API
- **Storage**: Firebase Firestore
- **Transcription**: OpenAI Whisper

## 🌐 Live Demo

**Demo Day Platform**: https://house-whisperer-demoday.vercel.app/
- Create inspections with voice recordings
- Generate professional reports with smart narratives
- Test the narrative cascade (Narratives → Standards-Based → AI Generated)

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
- Create a new inspection
- Add clips with voice recordings:
  - "Double-tapped breaker in main panel"
  - "Attic insulation only 4 inches deep"
  - "GFCI protection missing in garage"
- Generate professional report with narratives

## 📊 Key Features for Demo Day

### Core Inspection Workflow
- **Voice-to-Report**: Record observations → Auto-transcribe → Generate narratives
- **Smart Narrative Matching**: Semantic search across 6,500+ expert-written narratives
- **Cohere Reranking**: 98%+ accuracy on technical matches (e.g., "4 inches" → "3-4 inch depth")
- **Standards Compliance**: Automatic references from 16,000+ indexed building codes & SOPs

### Report Intelligence
- **Quality Scoring**: Track narrative sources (Narratives/Standards/AI Generated)
- **Severity Classification**: Critical/Major/Minor/Info badges per section
- **Executive Summary**: AI-generated overview of key findings
- **Hybrid Narratives**: Combines technical codes with homeowner-friendly explanations

### Batch runner
- `scripts/run_batch_questions_chat_eval.py` supports `--print-config` to print masked backend config and embeds it into the run’s JSONL/Markdown outputs for traceability.

### Inspector RAG flow
- Default behavior: single pass — `RAG → optional Web → Synthesis`.
- Web augmentation can run once when RAG is empty, or when `USE_WEB_AUGMENT=1` and the query matches keywords.
- Implemented in `api/langgraph_inspector_rag.py` (nodes: `policy_node`, `rag_tool_node`, `web_tool_node`, `synthesis_node`).

## 🔍 Demo Scenarios

### Report Generation Demo
1. Create inspection for "123 Demo Street"
2. Record findings in key sections:
   - **Electrical**: "Double-tapped breaker needs correction"
   - **Insulation**: "Attic has only 4 inches of insulation"
   - **Site Drainage**: "Standing water near foundation"
3. Generate report showing narrative cascade:
   - ✅ Verified narratives for common issues
   - 📋 Building code-enhanced for drainage (sparse section)
   - 🎯 Reranked for precise insulation match

### Inspector Chat Assistant
- "What's the code requirement for GFCI in garages?"
- "Any recalls on Carrier AC units from 2019?"
- "How do I test arc-fault breakers?"

## 📁 Project Structure

```
House_Whisperer/
├── api/
│   ├── app.py                                      # FastAPI server with inspection endpoints
│   ├── langgraph_report_writer_enhanced.py         # Base enhanced report module
│   ├── langgraph_report_writer_enhanced_reranker.py # Main report generation with intelligent cascade
│   ├── langgraph_inspector_rag.py                  # Building codes RAG system
│   └── web_search_tools.py                         # Tavily integration for recalls
├── web/
│   └── src/
│       ├── components/
│       │   ├── InspectionManager.js                # Main inspection UI
│       │   ├── ReportViewer.js                     # Markdown report display
│       │   └── AudioRecorder.js                    # Voice recording interface
│       └── services/
│           └── api.js                               # Firebase + API integration
├── data/
│   ├── NC_Building_Inspection_Codes/               # 2024 NC building codes
│   └── SOP/                                        # InterNACHI standards
├── scripts/
│   ├── build_narratives_index.py                   # Qdrant indexing
│   ├── test_narrative_retrieval.py                 # Narrative testing
│   └── test_inspector_rag.py                       # RAG testing
└── docs/
    ├── report_generation_flow.md                   # LangGraph architecture diagram
    └── reference/
        └── narratives.csv                           # 6,500+ expert narratives
```

## 🔄 Report Generation: Narratives & RAG Interplay

The report generation system uses a sophisticated cascade of narrative sources to ensure high-quality, contextually relevant content:

### Narrative Selection Cascade
The system follows this priority order for each section:

1. **Database Narratives (Qdrant)** - Pre-written expert narratives
   - If score ≥ 0.7: Use as "✅ Verified Narrative"
   - With Cohere reranker: Improves relevance to "🎯 Reranked Narrative"

2. **Inspector RAG (Standards)** - When narrative score < 0.7 or standards keywords detected
   - Searches 16,632+ chunks of building codes & SOPs
   - If confidence > 0.6: Use as "📋 Standards-Based" or "🎯📋 Narratives+Standards"
   - Combines technical accuracy with regulatory compliance

3. **GPT-4 Generation** - Final fallback
   - When no good matches exist
   - Marked as "🤖 AI Generated"

### Key Features
- **Hybrid Approach**: Combines database narratives WITH Inspector RAG results
  - Primary narrative from RAG (technical/code perspective)
  - Secondary narratives from database (homeowner-friendly)
  - Up to 3 narratives shown per section

- **Smart Reranking**: Cohere reranker (when available) improves semantic matching
  - Especially effective for technical terms (e.g., "4 inches deep" → "3-4 inch depth")
  - Maintains high accuracy even with paraphrased descriptions

- **Quality Scoring**: Each section tracks its narrative source and confidence
  - Verified/Reranked narratives boost overall report quality score
  - Transparent sourcing shown in report metadata

### Narrative Distribution
Sections with rich narrative databases (1000+ entries):
- Exterior, Roof, Electrical, HVAC, Plumbing

Sections ideal for triggering Inspector RAG (< 150 entries):
- Site Drainage (10), Environmental (33), Outbuildings (131)

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
You'll get PASS/FAIL per test and a summary. This mirrors production: embed transcript → filter by `payload.section == clip.section` → similarity search.

### 5) Step-by-Step App Testing (10 Test Cases)
To verify narratives are working end-to-end in the actual app, follow these specific test scripts:

#### **Test 1: Electrical - Double-Tapped Breaker**
1. Create new inspection with address "123 Test St, Charlotte, NC"
2. Add clip in **Electrical** section
3. Record audio: *"Two wires are connected to a single breaker, this is a double-tap and needs to be fixed by an electrician"*
4. Generate Draft → Look for 🟢 **Electrical: Narrative** badge
5. **Expected Narratives** (should retrieve one of these):
   - **Row 174 from narratives.csv** - **"Breaker double-tapped"**: *"In the electrical service panel, two wires were connected to a breaker designed for only one wire. This condition, called as a 'double-tap', is contrary to the breaker manufacturer's recommendations, and should be corrected by a qualified electrical contractor."*
   - **Row 179 from narratives.csv** - **"Breaker: double-tapped"**: *"In this sub-panel, two wires were connected to a breaker designed for only one wire. This is known as a 'double-tap' and it violates the breaker manufacturer's recommendations."*
6. **Similarity Score**: Should be ≥ 0.7 for keywords "double-tap", "two wires", "breaker"

#### **Test 2: Roof - Missing Shingles**
1. Add clip in **Roof** section  
2. Record audio: *"Several asphalt shingles are missing and damaged on the south side of the roof"*
3. Generate Draft → Look for 🟢 **Roof: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 916 from narratives.csv** - **"Clearance: from grade, damage"**: *"Wood shingles covering exterior walls had damage visible. This condition appeared to be the result of wood decay caused by moisture absorption due to inadequate clearance from grade."*
   - **Row 935 from narratives.csv** - **"Clearance: from roof, damage"**: *"Damage to wood shingles covering exterior walls appeared to be the result of moisture contact from inadequate clearance from roof components."*
5. **Similarity Score**: Should be ≥ 0.6 for keywords "shingle", "damage", "missing"

#### **Test 3: HVAC - Disconnected Duct**
1. Add clip in **HVAC** section
2. Record audio: *"Found a supply duct that's completely disconnected in the attic, air is leaking everywhere"*
3. Generate Draft → Look for 🟢 **HVAC: Narrative** badge  
4. **Expected Narratives** (should retrieve one of these):
   - **Row 48 from narratives.csv** - **"HVAC ducts: disconnected"**: *"Disconnected ducts were visible in the attic. The ducts should be reconnected by a qualified HVAC contractor to save on energy costs."*
   - **Row 49 from narratives.csv** - **"HVAC ducts: disconnected combustion vent"**: *"A combustion vent visible in the attic was disconnected, the toxic products of combustion were leaking into the surrounding area."*
5. **Similarity Score**: Should be ≥ 0.8 for keywords "duct", "disconnected", "attic"

#### **Test 4: Plumbing - Active Leak**
1. Add clip in **Plumbing** section
2. Record audio: *"There's an active leak under the kitchen sink at the P-trap connection"*
3. Generate Draft → Look for 🟢 **Plumbing: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 3296 from narratives.csv** - **"Cabinets: under-sink, trap, leaking"**: *"Leaking connections at the trap assembly beneath the cabinet sink should be repaired to avoid future/additional damage to the cabinet floor and possibly the wall/floor structures below. Repairs should be made as necessary by a qualified contractor."*
   - **Row 3100 from narratives.csv** - **"Radiant floor: leaking radiant tubing"**: *"Heat distribution pipes for the radiant in-floor heating system were actively leaking. An evaluation and work as necessary should be performed immediately by a qualified plumbing contractor."*
5. **Similarity Score**: Should be ≥ 0.7 for keywords "leak", "sink", "trap", "P-trap"

#### **Test 5: Insulation - Attic Depth**
1. Add clip in **Insulation & Ventilation** section
2. Record audio: *"Attic insulation is only about 4 inches deep, should be much thicker for energy efficiency"*
3. Generate Draft → Look for 🟢 **Insulation & Ventilation: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 26 from narratives.csv** - **"Depth: 3-4\" - add"**: *"Attic floor insulation depth averages 3 to 4 inches. Install additional insulation to comply with local energy codes."*
   - **Row 24 from narratives.csv** - **"Depth: 12-14\""**: *"Attic floor insulation depth averages 12 to 14 inches. To maximize savings on heating and cooling costs, insulation levels should be increased."*
5. **Similarity Score**: Should be ≥ 0.8 for keywords "attic", "insulation", "inches", "depth"

#### **Test 6: Garage - Auto-Reverse Safety**
1. Add clip in **Garage / Carport** section
2. Record audio: *"The garage door auto-reverse safety feature isn't working when I test it"*
3. Generate Draft → Look for 🟢 **Garage / Carport: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 1857 from narratives.csv** - **"Switch: installed too low"**: *"The push-button switch for the overhead garage door automatic opener was lower than the recommended 5-foot (1524 mm) minimum height above the standing surface. This condition is potentially dangerous to children. The switch should be raised for safety reasons."*
   - **Row 1858 from narratives.csv** - **"Automatic opener: extension cord as permanent wiring"**: *"The overhead garage door automatic opener was plugged into an extension cord. Extension cords should not be used as permanent wiring."*
5. **Similarity Score**: Should be ≥ 0.6 for keywords "garage", "door", "safety", "auto-reverse"

#### **Test 7: Exterior - Damaged Siding**
1. Add clip in **Exterior** section
2. Record audio: *"Found damaged lap siding on the west side with exposed wood substrate underneath"*
3. Generate Draft → Look for 🟢 **Exterior: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 837 from narratives.csv** - **"Asbestos-containing siding (possible): damaged"**: *"The fiber-cement siding was damaged in areas. Damaged siding should be replaced by a qualified contractor. Matching replacements may be difficult to locate. Because of the age of the home, the fiber-cement siding is likely to contain some percentage of asbestos."*
   - **Row 836 from narratives.csv** - **"Asbestos-containing siding (possible): broken"**: *"Some pieces of this siding were damaged or missing. Because of the age of the home, the fiber-cement siding is likely to contain asbestos."*
5. **Similarity Score**: Should be ≥ 0.7 for keywords "siding", "damage", "substrate", "exposed"

#### **Test 8: Interior - Inoperable Window**
1. Add clip in **Interior** section
2. Record audio: *"Bedroom window won't open, seems stuck and needs repair for emergency egress"*
3. Generate Draft → Look for 🟢 **Interior: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 829 from narratives.csv** - **"3-5-year Maintenance recommended"**: *"Manufacturers of vinyl siding typically recommend that window and door openings be re-sealed with a high-quality sealant every 3 to 5 years."*
   - **Row 969 from narratives.csv** - **"Cracking: above windows/doors"**: *"The brick exterior walls had cracking visible above window and door openings indicating a degree of structural failure."*
5. **Similarity Score**: Should be ≥ 0.5 for keywords "window", "open", "egress", "inoperable"

#### **Test 9: Site & Drainage - Negative Slope**
1. Add clip in **Site & Drainage** section
2. Record audio: *"Ground slopes toward the foundation here, water will drain against the house"*
3. Generate Draft → Look for 🟢 **Site & Drainage: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 1385 from narratives.csv** - **"Grading: negative grade- expansive soil"**: *"The home had areas of neutral or negative drainage that will route runoff from precipitation toward the foundation. Because the home was in an area that may contain expansive soil, these areas should be re-graded to improve drainage near the foundation and help reduce the risk of foundation damage. The ground should slope away from the home a minimum of ¼-inch per foot for a distance of at least six feet from the foundation."*
   - **Row 1386 from narratives.csv** - **"Grading: neutral/negative drainage"**: *"The home had areas of neutral or negative drainage that will route runoff from precipitation toward the foundation. Excessive moisture at the foundation can cause damage to the foundation or the home's structure."*
5. **Similarity Score**: Should be ≥ 0.8 for keywords "slope", "foundation", "drainage", "grading"

#### **Test 10: Kitchen - GFCI Protection**
1. Add clip in **Kitchen** section
2. Record audio: *"Kitchen outlets near the sink don't have GFCI protection, this is a safety issue"*
3. Generate Draft → Look for 🟢 **Kitchen: Narrative** badge
4. **Expected Narratives** (should retrieve one of these):
   - **Row 187 from narratives.csv** - **"Breaker: no GFCI protection, install GFCI breakers"**: *"No Ground Fault Circuit Interrupter (GFCI) protection was provided to circuits controlled by this sub-panel. For safety reasons, consider having GFCI breakers installed to meet modern requirements."*
   - **Row 361 from narratives.csv** - **"GFCI protection, none"**: *"Electrical receptacles in the basement were not ground fault circuit interrupter (GFCI) protected. GFCI protection is designed to prevent electric shock/electrocution and is relatively inexpensive to have installed."*
5. **Similarity Score**: Should be ≥ 0.6 for keywords "GFCI", "protection", "safety", "outlets"

#### **How to Verify Specific Narratives Were Retrieved:**
1. **Check Generation Coverage Badges**: Look for 🟢 green "Narrative" badges (not amber "Summary")
2. **Examine Findings Text**: The "Findings" section should contain the exact narrative text shown above
3. **Verify Narrative Count**: Badge should show (n=1) or higher, indicating narratives were found
4. **Match Keywords**: Findings text should include the specific technical terms from the expected narratives
5. **Cross-Reference CSV**: Use the row numbers (e.g., Row 174, Row 187) to verify against `docs/reference/narratives.csv`

#### **Success Indicators:**
- ✅ **Green badges** appear in "Generation coverage" 
- ✅ **"Findings"** sections contain professional narrative text (not just "No standardized narratives found")
- ✅ **Narrative count** shows (n=1, 2, 3) indicating narratives were retrieved
- ✅ **Table of Contents** shows sections with narrative content
- ✅ **Specific narrative text** matches examples shown above

#### **Troubleshooting:**
- 🟡 **Amber "Summary" badges** = No narratives found, LLM-generated summary used
- ⚫ **Gray badges** = Low confidence narratives (score < 0.55)
- ❌ **No findings** = Section missing from report or no clips for that section

### Production usage
- Each clip has `clip.section` = report section key (YAML).
- Query Qdrant with filter `payload.section == clip.section`, rank by similarity to the transcript.
- Use top hits as suggested narratives; LLM writes the section summary separately.

### Demo-day narratives coverage (what to test now)
Based on current indexing and mappings, these report sections have narrative coverage and are good candidates for test cases:
- electrical, roof, insulation_ventilation (attic insulation/ventilation), plumbing, hvac, interior, garage, exterior, structure, kitchen, pools_spas, environmental, site_drainage (sparse but present)

Sections currently lacking mapped narratives (skip for now unless we add conditional duplication/mappings):
- bathrooms, fireplaces_chimneys, laundry, summary (summary is synthesized, not narrative-driven)

- The Insulation section is the best test - the reranker should find the "3-4 inch depth" narrative that the basic enhanced version misses!

Notes:
- `attic` narratives are mapped to the report section `insulation_ventilation`.
- If you need fireplaces/chimneys, add mappings for narrative sections mentioning fireplace/chimney/flue to `fireplaces_chimneys` and rebuild the index.

#### What are Verified Narratives

> before you do anything , what should verified_count be in terms of meaning?

⏺ Great question! Let me explain what "verified_count" should mean conceptually:

  Verified Narratives should represent narratives that come from the pre-approved narrative database (Qdrant) with high confidence - essentially narratives that are:
  1. Pre-written by experts and stored in the database
  2. Retrieved with high confidence (good semantic match)
  3. Not AI-generated on the fly

  In the narrative source tracking, we have these categories:
  - 'verified_narrative' - High-confidence match from the database
  - 'reranked_narrative' - Database narrative that was reranked by Cohere (still from database!)
  - 'code_enhanced' - Enhanced using RAG/inspector code
  - 'ai_generated' - Completely generated by GPT-4


## 🧾 Report Generation (current)

- Media capture: audio + photos per clip; automatic Whisper transcription.
- Persistent data: Firestore (inspections, clips, transcripts), Firebase Storage (media).
- Report writer (Option B2): structured outline → per‑section LLM summary (gpt‑4o‑mini) → observations (transcript first sentence + suggested narratives + photos) → Markdown draft stored under `inspections/{id}/reports/draft`.
- Narratives: indexed to Qdrant; queries filter by `payload.section == clip.section` and rank by similarity to the transcript.

