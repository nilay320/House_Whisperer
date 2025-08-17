### Report Writer – Option C: Hybrid (S6 supervisor + S10 writer)

Purpose: supervisor for light routing, but core writing is outline→write.

Nodes
- supervisor_policy: decide plan_outline, optional retrieval, write_report, optional refine, finalize
- preprocess_inputs
- plan_outline
- retrieve_rag (optional)
- web_search (optional)
- write_report (S10-style writer using outline)
- refine_once (optional)
- finalize

Mermaid
```mermaid
flowchart TD
    START([start]) --> PP[preprocess_inputs]
    PP --> SUP{supervisor_policy}
    SUP -->|plan_outline| OUT[plan_outline]
    SUP -->|retrieve_rag| RAG[retrieve_rag]
    SUP -->|web_search| WEB[web_search]
    SUP -->|write_report| WR[write_report (outline->write)]
    SUP -->|refine_once| RF[refine_once]
    SUP -->|finalize| FIN[finalize]

    OUT --> SUP
    RAG --> SUP
    WEB --> SUP
    WR --> SUP
    RF --> SUP
    FIN --> END([end])
```

Default behavior (Demo Day)
- USE_REPORT_RAG=0, USE_REPORT_WEB_AUGMENT=0; supervisor still runs but likely goes plan_outline → write_report → finalize
- Temp 0.2; cap steps to 4–5

Pros
- Supervisor exists (your requirement) without heavy loops
- Writer quality/coherence from S10 pattern

Cons
- Slightly more complex than Option B
- Still not a full ReAct loop

Separation
- Independent from Inspector RAG; own flags and endpoint

Outputs
- report_markdown, sections[], trace-based sources (if retrieval/Web used), timings_ms{}

When to choose
- You want a supervisor now and S10-quality writing, with minimal latency.

