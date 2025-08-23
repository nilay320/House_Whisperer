# Report Generation Flow - LangGraph Architecture

## Overview
The report generation system uses LangGraph to orchestrate a multi-node workflow that processes inspection data through various enrichment stages.

## Visual Flow Diagram

```mermaid
graph TD
    Start([Start]) --> LoadData[Load Data<br/>node_load_data]
    LoadData --> GroupBySection[Group by Section<br/>node_group_by_section]
    GroupBySection --> RetrieveNarratives{Retrieve Narratives<br/>node_retrieve_narratives_with_reranker}
    
    %% Narrative Retrieval Sub-flow
    RetrieveNarratives --> QdrantSearch[Search Qdrant<br/>Vector Database<br/>6,576 narratives]
    
    QdrantSearch --> CodeCheck{Code Keywords<br/>Detected?}
    
    CodeCheck -->|No| ScoreCheck{Score Check}
    CodeCheck -->|Yes| TriggerRAG[Trigger RAG<br/>Enhancement]
    
    ScoreCheck -->|≥0.7 or<br/>Reranked ≥0.6| VerifiedNarrative[✅ Verified/🎯 Reranked<br/>Narrative Only]
    ScoreCheck -->|<Threshold| TriggerRAG
    
    TriggerRAG --> InspectorRAG[Inspector RAG<br/>_query_inspector_rag]
    
    InspectorRAG --> RAGCheck{Confidence > 0.6?}
    
    RAGCheck -->|Yes| HybridNarrative[🎯📋 Narrative + Code<br/>Combined Result]
    RAGCheck -->|No| GPTGenerate[GPT-4 Generation<br/>_generate_custom_narrative]
    
    GPTGenerate --> AIWithNarrative[🤖 AI + Database<br/>Combined]
    
    %% No narratives path
    QdrantSearch -->|No Matches| DirectRAG[Try RAG First]
    DirectRAG --> InspectorRAG
    
    %% Convergence
    VerifiedNarrative --> CombineResults[Combine Results<br/>Up to 3 narratives]
    HybridNarrative --> CombineResults
    AIWithNarrative --> CombineResults
    
    CombineResults --> AssembleMarkdown[Assemble Markdown<br/>node_assemble_enhanced_markdown]
    
    AssembleMarkdown --> SaveDraft[Save Draft<br/>node_save_draft]
    SaveDraft --> End([End])
    
    %% Style
    classDef nodeStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef decisionStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef narrativeStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef ragStyle fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class LoadData,GroupBySection,AssembleMarkdown,SaveDraft nodeStyle
    class ScoreCheck,RAGCheck decisionStyle
    class VerifiedNarrative,BuildingCodeEnhanced,AIGenerated narrativeStyle
    class InspectorRAG,QdrantSearch,CohereRerank ragStyle
```

## Node Descriptions

### 1. **Load Data** (`node_load_data`)
- **Input**: `inspection_id`, `sections_filter`
- **Process**: Fetches clips from Firestore
- **Output**: `clips`, `inspection_meta`

### 2. **Group by Section** (`node_group_by_section`)
- **Input**: `clips`
- **Process**: Groups clips by their section (e.g., electrical, plumbing)
- **Output**: `grouped` (Dict[section_key, List[clips]])

### 3. **Retrieve Narratives** (`node_retrieve_narratives_with_reranker`)
The core intelligence node with cascading fallbacks:

#### 3a. **Qdrant Search**
- Searches 6,576 pre-written expert narratives
- Uses OpenAI embeddings (text-embedding-3-small)
- Filters by section for relevance

#### 3b. **Score Evaluation & Code Compliance Check**
**First, check for code-related keywords**: 'code', 'violation', 'standard', 'requirement', 'compliance', 'safety'

**Decision Logic:**
- **High confidence AND no code keywords**:
  - Reranked with score ≥ 0.6 → 🎯 Reranked Narrative
  - Non-reranked with score ≥ 0.7 → ✅ Verified Narrative
  
- **Low confidence OR code keywords mentioned**:
  - Trigger RAG enhancement
  - **Result**: 📋 Building Code-Enhanced + original narratives
  - Combines RAG result with top 2 database narratives

#### 3c. **Inspector RAG** (Enhancement/Fallback)
- Triggered when:
  - Low confidence narratives (< thresholds)
  - Code compliance keywords detected
  - No narratives found at all
- Searches 16,632 chunks of NC Building Codes & SOPs
- Uses `inspector-standards-postmidterm` collection
- If confidence > 0.6: Adds code-compliant narrative to existing ones

#### 3d. **GPT-4 Generation** (Last Resort)
- Only when RAG confidence ≤ 0.6 or RAG fails
- Generates custom narrative
- Still combined with database narratives if available
- Result: 🤖 AI Generated + database narratives

### 4. **Assemble Markdown** (`node_assemble_enhanced_markdown`)
- Combines all narratives into professional report format
- Includes executive summary, quality metrics
- Generates severity badges and source attribution

### 5. **Save Draft** (`node_save_draft`)
- Persists to Firestore (`reports/draft`)
- Returns final markdown and metadata

## Decision Flow Summary

### When Each Source is Used:
1. **✅/🎯 Database Only**: 
   - High confidence (≥0.7 or reranked ≥0.6) 
   - AND no code compliance keywords

2. **🎯📋 Narrative + Building Code (Hybrid)**:
   - Database narratives exist AND:
     - Low confidence (<thresholds) OR
     - Code keywords detected ('code', 'violation', 'standard', 'safety', etc.)
   - RAG confidence > 0.6
   - Combines both database narratives and RAG results

3. **📋 Building Code Only**:
   - NO database narratives found
   - RAG confidence > 0.6

4. **🤖 AI Generated + Database**:
   - RAG confidence ≤ 0.6 or RAG admits no relevant info
   - Still combines with database narratives if available

### Important Notes:
- **Code keywords trigger RAG**: Even high-quality narratives get RAG enhancement if code compliance mentioned
- **Narratives are preserved**: Database narratives are combined with RAG/AI, not replaced
- **Smart confidence detection**: RAG responses saying "couldn't find relevant" get low confidence

## State Management

The system uses `ReportState` (TypedDict) to maintain state across nodes:

```python
class ReportState(TypedDict):
    inspection_id: str
    sections_filter: Optional[List[str]]
    clips: List[Dict]
    grouped: Dict[str, List[Dict]]
    narratives_by_section: Dict[str, List[Dict]]
    narrative_sources: Dict[str, str]  # 'verified_narrative', 'reranked_narrative', 'hybrid_code_narrative', 'building_code_enhanced', 'ai_generated'
    section_severity: Dict[str, str]   # 'critical', 'major', 'minor', 'info'
    quality_scores: Dict[str, float]
    rag_results: Dict[str, Dict]
    markdown: str
    executive_summary: str
    report_quality_score: float
```

## Key Technologies

- **LangGraph**: Orchestration framework for multi-node workflows
- **Qdrant**: Vector database for narrative storage (1536-dim embeddings)
- **Cohere**: Reranking API for improved semantic matching
- **OpenAI**: Embeddings (text-embedding-3-small) and generation (GPT-4)
- **Firestore**: Persistence layer for inspection data and reports

## Configuration

Environment variables control behavior:
- `USE_ENHANCED_REPORT=1`: Enable enhanced report writer
- `COHERE_API_KEY`: Enable reranking (auto-detected)
- `REPORT_LOGS=1`: Enable debug logging to see cascade
- `QDRANT_COLLECTION`: Default `narratives_v1`
- `EMBEDDING_MODEL_NAME`: Default `text-embedding-3-small`

## Performance Characteristics

- **Narrative Retrieval**: ~200-500ms per section
- **Cohere Reranking**: +100-200ms when enabled
- **Inspector RAG**: ~2-5s when triggered
- **GPT-4 Generation**: ~3-5s when needed
- **Total Report Generation**: 10-30s depending on sections and fallbacks

## Quality Assurance

The system tracks quality at multiple levels:
- **Per-section quality scores**: Based on narrative source and confidence
- **Overall report quality**: Weighted average with bonus for verified narratives
- **Source attribution**: Every narrative tagged with its origin
- **Severity tracking**: Critical, Major, Minor, Info badges

## Example Output Structure

```markdown
# 🏠 Professional Home Inspection Report

## 📊 Report Quality Metrics
- Overall Quality Score: 85%
- Verified Narratives: 7/10

## 📋 Executive Summary
[AI-generated summary of key findings]

## Electrical
🔴 **Critical** • ✅ **Verified Narrative** (92% match)

### Findings & Recommendations
1. Double-tapped breaker observed...
2. 📋 Per NEC 408.41, each circuit breaker shall... (Building Code-Enhanced)
3. Consider panel upgrade for safety...

### Inspection Notes
- Two wires connected to single breaker
```

This architecture ensures every section receives appropriate narratives through intelligent cascading with transparent sourcing.