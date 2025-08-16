# Inspector RAG: Tuning Ideas and Next Steps

This note collects safe, incremental improvements we can apply to the Inspector Standards RAG and policy loop. Use as a living checklist; we can prioritize per Demo Day needs.

## Retrieval parameters (Qdrant)
- **Score threshold**
  - Current: `score_threshold = 0.55`
  - Option: lower to `0.4–0.5` to improve recall; rely on synthesis to filter
- **Limits and diversity**
  - Current: `limit = 6`, max 3 per source, final top 5
  - Option: `limit = 12–15`, keep 2–3 per source, final top 8–10
- **Search params**
  - Current: `{ hnsw_ef: 128, exact: false }`
  - Option A: increase `hnsw_ef` to `256–512` (better recall, small latency hit)
  - Option B: `exact: true` for short queries (brute-force, may add latency)

## Query rewriting (policy → RAG)
- If query mentions brand/authority, bias the RAG query:
  - “InterNACHI” → prefix with “InterNACHI Standards of Practice …”
  - “NCHILB” → “NCHILB Standards/Rules …”
  - “NC Building Code” → add code keywords (e.g., “2018/2020/2024 NC building code section …”)
- Add a minimal synonym map for common phrases (e.g., “deck railing” → “guard/handrail height”).

## Corpus / payload hygiene
- Ensure payload per point:
  - `source`: InterNACHI SOP | NCHILB | NC Building Codes
  - `type`: `regulatory`
  - `category`: `Standards`
  - `content`: concise, section-aware chunk
- Re-ingest InterNACHI SOP if missing; verify Qdrant collection contains roof-related SOP chunks.

## Policy loop behavior (graph)
- Current (simplified): policy → RAG once; if empty → Web once → Synthesis
- Guardrails:
  - Always synthesize after first successful RAG or Web step
  - Do not bounce back to RAG once Web is tried (v1)
- Optional later:
  - After Web, re-query RAG with a targeted section (only if needed for exact regulatory text)

## Synthesis safeguards
- If `context` and `web_results` both empty, produce a helpful fallback explaining that no relevant standards were found and suggest authoritative links (CPSC/manufacturer) rather than an empty answer.
- Prefer regulatory sections first; label “Practical guidance” from Web separately.

## Observability
- Log per query:
  - `policy_decisions` (sequence of actions)
  - `rag_hits` count, `web_hits` count
  - `elapsed_ms_total`, `elapsed_ms_rag`, `elapsed_ms_web`, `elapsed_ms_synth`
- Surface these in `/api/test-rag` for quick sanity.

## Web search precision (when needed)
- For recalls: bias to `site:cpsc.gov` and manufacturer domains; add year filter to query.
- Cap results (top 3–5) and normalize title/url/source for clean display.

## Nice-to-have (post Demo Day)
- “Best practices” augmentation after regulatory answer (1 short web step → label clearly)
- Section-aware retrieval (RAG) using simple headings/ids in chunk metadata
- Lightweight reranker on RAG hits (e.g., cosine + heuristic rerank)

## Action checklist
- [ ] Lower `score_threshold` to 0.5 and bump `limit` to 12
- [ ] Add InterNACHI/NCHILB/NCBC query rewrites in `policy_node`
- [ ] Verify/repair InterNACHI SOP ingestion; check roof sections present
- [ ] Add counters/metrics to logs; extend `/api/test-rag`
- [ ] (Optional) Increase `hnsw_ef` to 256; measure latency delta
