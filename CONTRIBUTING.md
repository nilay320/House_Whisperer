# Contributing Guide

This repo uses a safe workflow optimized for fast iteration with explicit approval gates.

## Branching & PRs
- Always work on a feature branch (e.g., `feature/report-writing-pwa-voice`).
- Open a PR to `main` when ready. Never push directly to `main`.

## Commit/Push Policy
- Do NOT commit or push code until the requester has tested locally and explicitly says "commit".
- Loop:
  1. Propose edits and provide local test steps.
  2. Requester tests and gives feedback.
  3. On "commit", stage, commit, and push to the feature branch.

## Local Test Checklist (Web)
- Frontend
  - `cd frontend && npm install && npm start`
  - `.env.local` contains all `REACT_APP_*` vars (incl. `REACT_APP_API_URL`).
- Backend
  - `uvicorn app:app --reload --port 8000 --app-dir api`
  - Env: `OPENAI_API_KEY` (+ `QDRANT_URL`, `QDRANT_API_KEY`, `TAVILY_API_KEY` when needed).
- Firebase
  - Google Auth enabled; Firestore created; Storage enabled.
  - Firestore rules (dev): authenticated users only.

## Security & Secrets
- Never commit secrets; use local env vars or `.env.local` (gitignored).
- Rotate exposed secrets immediately.

## Code Style
- Small, focused edits; avoid unrelated refactors.
- Clear naming; brief docstrings for non-obvious code.
- Keep lints clean; fix UX-impacting warnings.

## CI/CD (future)
- Gate merges on passing build/tests and basic e2e checks.

If in doubt, defer to the requester before committing.
