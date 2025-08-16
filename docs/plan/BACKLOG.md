# BACKLOG (Demo Day -> Post Demo)

Use this as the single prioritized backlog. When promoting an item, create an issue and link back here. For RAG tuning ideas, see `docs/Inspector_RAG_Tuning_Improvements.md` and reference specific bullets.

## Now (Demo Day focus)
- Report writing MVP
  - Endpoint: `POST /api/generate_report` (SSE) — inputs: transcript, photos[{url, caption}] — outputs: {json_report, markdown}
  - Deterministic LangGraph: policy_plan -> rag_lookup (per section) -> write_section -> consolidate -> finalize
  - Acceptance: ≤15s end-to-end; clear sections; cites regs when available
- Audio transcription
  - Endpoint: `POST /api/stt` — accepts webm/mp4/m4a; returns {transcript, duration}
  - Acceptance: ≥60s audio in ≤10s; editable transcript on frontend
- Photo capture/captions
  - Upload to Firebase Storage; optional `POST /api/caption` (vision) for suggested captions
  - Acceptance: ≥5 photos; editable captions; stored with report draft
- Frontend PWA: ReportWriter screen
  - AudioRecorder, PhotoCapture, DraftPreview (Markdown), Generate Draft
  - Persist draft to Firestore; reloadable via /inspector/report/:id

## Next (nice-to-have before Demo Day)
- Helpfulness gate (post-synthesis, single pass)
  - Flag: `USE_HELPFULNESS_GATE=1`
  - Node: rate 1–5 on: answers the question, cites regs when available, labels web vs regs
  - Action: if score < 3 and `ctx==0`, force one web augmentation retry; else return as-is
  - Telemetry: log score and decision; never loop more than once
  - Acceptance: gate never adds >1 extra LLM call; no blank responses; logs include `helpfulness_score`
- Sources UX
  - Hide no-URL web items from “Sources” display but keep content for synthesis
  - Acceptance: list shows only items with URLs; counts match returned URLs

## Later (post Demo Day)
- Retrieval upgrades
  - Section-aware chunk metadata; optional reranker; `hnsw_ef` tuning
- Web augmentation policy
  - Move keywords to persisted config; add per-keyword min_score overrides
- Observability
  - `/api/run/{id}` to fetch trace summary; structured JSON logs

---
Last updated: keep items small, with acceptance criteria. Link issues next to each item when created.
