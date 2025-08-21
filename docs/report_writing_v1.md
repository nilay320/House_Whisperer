### Report Writing v1 – Architecture (Option B core with narratives on)

**What this covers**
- **Generate Draft** endpoint that compiles sectioned Markdown from transcripts and photos.
- Narratives (docs/reference/narratives.csv) ON by default; keyword‑matched per section.
- Stores draft to Firestore and returns it to the client.

**Tech stack**
- **Backend**: FastAPI (Python), Firebase Admin SDK, OpenAI API (gpt‑4o‑mini + Whisper), httpx, asyncio
- **Frontend**: React PWA, Firebase Web SDK (Auth, Firestore, Storage)
- **Data**: Firestore (inspections, clips, reports), Firebase Storage (audio/photos), YAML sections, CSV narratives

**Primary endpoint**
- `POST /api/generate_report` → reads `inspections/{id}/clips/*` from Firestore, loads `api/config/report_sections.yaml` and `docs/reference/narratives.csv`, summarizes each section, composes observations (transcript first sentence + suggested narratives + photos), assembles Markdown, stores to `inspections/{id}/reports/draft` and returns `{ markdown, sectionCount, clipCount }`.

**Flags / config**
- `USE_REPORT_NARRATIVES=1` (default)
- `OPENAI_API_KEY` (backend)
- `FIREBASE_SERVICE_ACCOUNT_JSON` (backend)
- `api/config/report_sections.yaml` drives the canonical sections for both UI and backend

**Flow summary**
- Inspector records audio and attaches photos in the PWA → uploads to Storage; clip doc written to Firestore.
- Backend worker downloads audio, calls Whisper, writes transcript + status to Firestore.
- User clicks Generate Draft → backend groups clips by section → optional section summary via GPT‑4o‑mini → observations include transcript evidence, suggested narratives, and photo captions → Markdown assembled and stored.

**Diagram**

```mermaid
graph TD
  A["Inspector (Web PWA)<br/>(React + Firebase Client SDK)"] --> B["Firebase Storage<br/>(audio/photos)"]
  A --> C["Firestore (client writes)<br/>inspections/{id}/clips/*"]
  
  subgraph "Context: Media Transcription (pre-req)"
    D["FastAPI Backend<br/>(asyncio worker)"] -->|"download audio"| B
    D -->|"Whisper call"| E["OpenAI Whisper API"]
    D -->|"update transcript/status"| F["Firestore (Admin SDK)"]
  end

  A -->|"click Generate Draft"| G["POST /api/generate_report<br/>(FastAPI)"]
  G --> H["Firestore (Admin SDK)<br/>read clips for inspection"]
  G --> I["Load sections YAML<br/>api/config/report_sections.yaml"]
  G --> J["Load narratives CSV<br/>docs/reference/narratives.csv"]
  H --> K["Group clips by section key"]
  I --> K
  J --> K
  
  subgraph "Section Drafting (Option B core)"
    K --> L["For each section:<br/>summarize context (LLM)<br/>model: gpt-4o-mini"]
    L --> M["Compose Observations:<br/>- transcript first sentence<br/>- suggested narratives (keyword match)<br/>- photos + captions"]
  end

  M --> N["Assemble Markdown report"]
  N --> O["Firestore (Admin SDK)<br/>inspections/{id}/reports/draft"]
  N --> P["HTTP JSON response<br/>{ markdown, sectionCount, clipCount }"]
  P --> A

  Q["Flags/Config:<br/>- USE_REPORT_NARRATIVES=1 (default)<br/>- OPENAI_API_KEY (backend)<br/>- FIREBASE_SERVICE_ACCOUNT_JSON (backend)<br/>- Sections YAML drives UI + backend"]
```

**Notes**
- The supervisor layer (Option C) can wrap this flow later without changing data contracts.
- Suggested narratives are heuristic keyword matches; we can swap in semantic matching post‑demo.

### LangGraph nodes (logical) and LLMs

Although v1 is implemented inline in a FastAPI endpoint (not a literal LangGraph graph yet), the pipeline maps cleanly to the following nodes. This makes it easy to wrap with a thin supervisor later (Option C) without changing data contracts.

```mermaid
graph TD
  ST["Start"] --> LS["Load Sections\n(YAML)"]
  ST --> LN["Load Narratives\n(CSV)"]
  ST --> FC["Fetch Clips\n(Firestore)"]

  LS --> GB["Group by Section"]
  LN --> GB
  FC --> GB

  GB -->|for each section| SS["Section Summarize\nLLM: gpt-4o-mini (T=0.2)"]
  SS --> CO["Compose Observations\n(transcript first sentence +\nkeyword-matched narratives + photos)"]
  CO --> AM["Assemble Markdown"]
  AM --> SD["Save Draft\n(Firestore reports/draft)"]
  AM --> RESP["Return JSON\n{ markdown, sectionCount, clipCount }"]

  classDef llm fill:#eef,stroke:#36c;
  class SS llm;
```

Planned supervisor (Option C): add a `Supervisor` node to orchestrate per-section steps (apply guards, retries, optional grading) while keeping `SS/CO/AM/SD` node contracts the same.


