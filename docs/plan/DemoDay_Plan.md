# Demo Day Implementation Plan: Inspector Report Writing (PWA + Voice) and Future Buyer RAG

## 0) Branch, scope, baseline
- Working branch: `feature/report-writing-pwa-voice` (branched from your post‑midterm state)
- Reference (ideas only): `feature/home-inspection-ai-assistant` – web/mobile scaffolding and patterns
  - https://github.com/nilay320/House_Whisperer/tree/feature/home-inspection-ai-assistant
- Preserve as-is: Inspector agentic RAG over Qdrant Cloud (InterNACHI SOP, NCHILB, NC Building Codes) with Tavily web search.

## 1) Current state (starting point)
- Backend
  - Agentic RAG (LangGraph) using Qdrant Cloud and Tavily.
- Frontend
  - CRA web app, Google auth and role gating in progress.
  - PWA scaffolding partially present (manifest/SW need validation + polish).
- Infra
  - Firebase: Auth (Google), Firestore (created), Storage (to enable for audio/photos).

## 2) Phase A (NOW): Inspector Report Writing + PWA polish
Deliver a professional mobile-first Inspector workspace that goes from Voice → STT → Draft → Export.

### 2.1 Voice notes (Inspector-only)
- Capture: MediaRecorder (audio/webm), mobile-friendly UX, clear start/stop states.
- Upload: Firebase Storage path `inspections/{inspectionId}/voice-notes/{noteId}.webm` with progress + retries.
- STT: FastAPI `/api/stt` (OpenAI Whisper) → timestamped transcript segments.
- Persist: Firestore
  - `inspections/{inspectionId}`: { createdBy, createdAt, status }
  - `inspections/{inspectionId}/notes/{noteId}`: { storagePath, durationMs, createdAt }
  - `inspections/{inspectionId}/transcripts/{noteId}`: { segments: [{start,end,text}], status }

### 2.2 Photos (Phase A ready; association polished over time)
- Capture/upload with mobile-friendly file input.
- Storage path `inspections/{inspectionId}/photos/{photoId}.jpg`.
- Associate photos to nearest transcript segments (time proximity + heuristic prompt), editable mapping.

### 2.3 Draft generation
- Endpoint: `/api/generate_report` given `{ inspectionId }`.
- Uses existing agent (LangGraph) to map transcripts → structured sections aligned to InterNACHI/ASHI with defect narratives.
- Output JSON:
```
{
  "sections": [
    { "id": "roof", "title": "Roof", "narrative": "...",
      "defects": [
        { "id": "d1", "title": "Shingle wear", "description": "...", "severity": "moderate", "images": ["photoId1"] }
      ]
    }
  ],
  "metadata": { "inspectionId": "...", "generatedAt": "..." }
}
```

### 2.4 Editor + export
- Inline editor for sections/narratives/defects.
- Export PDF (simple, reliable layout) and JSON. “Publish” reserved for Phase B.

### 2.5 Auth & roles (finalize)
- Google-only auth.
- First login: prompt role once (Inspector/Buyer) → save `users/{uid} { role }`.
- Returning users: auto-route by role. Inspector sees workspace; Buyer sees buyer landing (chat to come later).

### 2.6 PWA polish (immediate)
- Valid manifest + icons (192/512) and link tags.
- Service worker registration (app shell caching; no API caching).
- Mobile meta tags (replace deprecated ones; add `mobile-web-app-capable`).
- Permissions UX for mic/camera; install prompt verified.

## 3) Phase B (next): Buyer RAG (new)
- “Publish report” action:
  - Flatten finalized report text → index into Qdrant as per‑report collection (metadata: reportId, inspectorId).
- Buyer chatbot UI:
  - Retrieval plan: query report collection first; enrich with SOP/Code when needed.
  - Answers with citations (section IDs and SOP/Code references).

## 4) Backend (FastAPI) – endpoints & config
- Endpoints (additive):
  - `POST /api/stt` (multipart audio) → `{ transcript: [{start,end,text}], lang, durationMs }`
  - `POST /api/generate_report` → `{ inspectionId }` → draft JSON
  - `POST /api/publish_report` (Phase B) → `{ inspectionId }` → index to Qdrant
- Env/config:
  - `OPENAI_API_KEY` (Whisper + LLM)
  - Qdrant: `QDRANT_URL`, `QDRANT_API_KEY`
  - Tavily: `TAVILY_API_KEY` (existing)

## 5) Frontend (CRA) – Inspector workspace
- Route `/inspector` (role‑gated):
  - VoiceCapture (record/upload/progress)
  - PhotoCapture (capture/upload)
  - TranscriptPanel (segments, status)
  - DraftEditor (sections/defects; approve/edit)
  - ExportActions (PDF/JSON; publish later)
- State flow: inspectionId → recordings → STT → transcript → draft → edits → export/publish.
- PWA: installable; mic/camera smooth on iOS/Android.

## 6) Security/rules (dev-ready)
- Firestore rules:
```
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```
- Storage: authenticated users; per‑user/inspection paths (tighten later).

## 7) Acceptance criteria (Phase A)
- Voice → transcript under 20s for a 30–60s note; progress + retries visible.
- Draft generated with sensible sections/defect narratives; fully editable.
- Export PDF in <5s with clean formatting.
- Auth flow: first login prompts role once; returning users auto‑route.
- PWA installable; mic/camera permission flows work on iOS/Android.

## 8) Risks & mitigations
- Whisper latency/cost → chunk/batch STT, progress UI, retry.
- iOS Safari quirks → explicit user gestures, https, file input fallback.
- Draft quality → prompt tuning + “defect library”; editor ensures human‑in‑the‑loop.
- Quotas/limits → moderate media sizes, consider client‑side image compression.

## 9) Timeline (≤ 2 weeks)
- Days 1–2: PWA polish; finalize Google auth + role gating; Storage rules; voice capture/upload scaffold.
- Days 3–4: `/api/stt` + transcript viewer; UX states (pending, error, retry).
- Days 5–6: `/api/generate_report` + editor wiring; initial narratives/templates.
- Days 7–8: Export PDF/JSON; basic publish stub.
- Days 9–10: Mobile testing; polish; demo script; stabilize.

## 10) Test plan
- Unit: parse Whisper output; map transcripts → draft schema.
- Integration: mobile e2e (record → transcript → draft → export).
- Smoke: Google auth + role paths; offline upload fallback; PDF on mobile.

## 11) Task checklist (Phase A)
- [ ] PWA: manifest/icons/meta/SW validated
- [ ] Google-only auth + one‑time role prompt finalized
- [ ] Voice capture (MediaRecorder) + upload to Storage with progress
- [ ] `/api/stt` Whisper endpoint + transcript persistence
- [ ] Draft generation endpoint + editor UI
- [ ] Export PDF/JSON
- [ ] QA on iOS/Android browsers

---
Owner split
- Nilay: Backend endpoints, draft generation wiring, Inspector UI logic, PWA polish.
- Raghu: Editor UX, narratives/templates, export polish, demo prep.

Reference branch (ideas only):
- https://github.com/nilay320/House_Whisperer/tree/feature/home-inspection-ai-assistant


