# Home Inspector AI Assistant - Certification Challenge

---

## Task 1: Defining your Problem and Audience

### ✅ Deliverables

**Write a succinct 1-sentence description of the problem**

Home inspectors face legal risk because they're expected to follow building codes and inspection standards to the dot, and those codes and changing standards aren't easily accessible.

**Write 1-2 paragraphs on why this is a problem for your specific user**

Most Home Inspectors commit to a 24 hour turnaround time to inspect a house and provide a detailed report on their inspection to the buyer. While most Inspectors enjoy the inspection work where they apply their expertise, several report that they might be the "most sued" professionals, since a minor error and mismatch with SOP can turn into a major issue.

Inspectors are required to comply with various Standards of Practice (SOPs) such as InterNACHI, ASHI, and state-specific rules like NCHILB in North Carolina. Yet these documents, especially state building codes, are not always publicly accessible or easy to search. This increases liability if the inspector misinterprets or omits something critical.

**Key findings from user interviews:**
- Inspectors are legally bound to codes and SOPs that are difficult to access and time intensive.
- There is an existing critical time management issue and even self reported growing burnout (from after-hours report-writing and answering Buyer calls) which exacerbates the aforementioned problem.

---

## Task 2: Propose a Solution

### ✅ Deliverables

**Write 1-2 paragraphs on your proposed solution. How will it look and feel to the user?**

Our solution is a web-based AI chat assistant that home inspectors can access from their computers when writing reports or researching compliance questions.

Inspectors type their questions in natural language - like "What's the required clearance for electrical panels in NC?" or "Are there any recalls on Federal Pacific breakers?" The system instantly provides comprehensive answers combining official standards with current best practices, complete with source citations.

The experience feels like having a senior inspector mentor available during report writing. Instead of searching through multiple PDFs or websites, inspectors get immediate, authoritative answers with clear distinctions between mandatory requirements and recommended practices. The interface shows real-time progress as the AI searches through regulations and web sources, building trust through transparency. For inspectors who often spend hours after inspections researching requirements and writing reports, this means faster report completion and increased confidence in their compliance. Each question receives a thorough, standalone response drawing from both regulatory documents and current web sources, ensuring inspectors always get the most complete and up-to-date information available.

**Describe the tools you plan to use in each part of your stack. Write one sentence on why you made each tooling choice.**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **LLM** | gpt-4o-mini (OpenAI) | Chosen for fast, cost-efficient performance with strong reasoning. |
| **Embedding Model** | text-embedding-3-small (OpenAI) | Provides optimal balance of performance and cost for semantic search of inspection documents. |
| **Orchestration** | LangGraph with multi-agent architecture | Enables intelligent routing between specialized agents (research, web search, synthesis) for comprehensive answers. |
| **Vector Database** | Qdrant | Selected for its fast performance, robust filtering, and open-source flexibility. |
| **Monitoring** | Custom SSE streaming (current), LangSmith (production) | Currently provides real-time progress updates, LangSmith planned for production observability and was used for performance testing in Task 7. |
| **Evaluation** | RAGAS + Golden Test Set | To validate retrieval quality and grounding accuracy. |
| **User Interface** | React web app with responsive chat interface | Browser-based chat interface optimized for desktop use, providing intuitive Q&A experience for inspectors |
| **Serving & Inference** | Vercel + Railway for application serving, OpenAI for model inference | Distributed architecture with Vercel hosting the frontend, Railway hosting the API, and OpenAI providing managed model inference. |

**Where will you use an agent or agents? What will you use "agentic reasoning" for in your app?**

Our application employs a multi-agent workflow orchestrated by LangGraph with four specialized nodes:

1. **Supervisor Node** - Uses deterministic routing logic to direct queries based on content analysis and system state
2. **Research Node** - Performs vector similarity search in our Qdrant database of inspection standards
3. **Web Search Node** - Calls Tavily API for real-time information on recalls, manufacturers, and current practices
4. **Synthesis Node** - Uses GPT-4o-mini to generate comprehensive responses from gathered context

**Agentic reasoning is demonstrated through:**
- **Stateful orchestration** - The supervisor maintains workflow state and makes routing decisions based on previous results
- **Adaptive workflow** - System dynamically chooses different paths based on query content (e.g., detecting "recall" triggers web search)
- **Intelligent fallbacks** - When RAG returns no results, system automatically attempts web search
- **Multi-step execution** - Breaks complex queries into retrieval → synthesis steps

This orchestrated approach combines the reliability of deterministic routing with the power of LLM generation, ensuring comprehensive responses that simple RAG cannot achieve.

---

## Task 3: Dealing with the Data

### ✅ Deliverables

**Describe all of your data sources and external APIs, and describe what you'll use them for.**

**Vector Database Sources (RAG):**

Our Qdrant Cloud collection ('inspector-standards') contains three document sets:

1. **InterNACHI Standards of Practice** - International standards defining scope of home inspections, inspector responsibilities, and ethical guidelines
2. **NC Home Inspector Licensure Board (NCHILB) Standards** - North Carolina-specific licensing requirements, state regulations, and enforcement procedures
3. **NC Building Codes 2024** - Current North Carolina residential building codes covering structural, electrical, plumbing, fire safety, fuel gas, energy, and mechanical requirements

**Purpose:** These documents provide the authoritative foundation for answering regulatory compliance questions, inspection procedures, and code requirements.

**External API:**

**Tavily Search API** - Real-time web search across the internet

**Purpose:** Captures current information not in our vector database, including recent best practices, product recalls, code updates, and practical field guidance from industry websites

**Describe the default chunking strategy that you will use. Why did you make this decision?**

**Default Chunking Strategy:** RecursiveCharacterTextSplitter with 1000 character chunks and 200 character overlap

**Parameters:**
- Chunk size: 1000 characters
- Overlap: 200 characters
- Separators hierarchy: ["\n\n", "\n", ". ", ".", " ", ""]

**Rationale:**

RecursiveCharacterTextSplitter preserves document structure by splitting at natural boundaries (paragraphs, sentences) before character limits. The 1000-character chunks maintain sufficient context for complex inspection procedures while enabling accurate semantic search. The 200-character overlap prevents information loss at boundaries - critical for multi-part regulations that span chunks. This approach is ideal for technical documents with numbered procedures and regulatory language requiring semantic coherence.

**[Optional] Will you need specific data for any other part of your application? If so, explain.**

Currently in communication with InterNACHI exploring partnership opportunities to ingest 7,500 Inspection Narratives data (future iteration)

---

## Task 4: Building a Quick End-to-End Agentic RAG Prototype

### ✅ Deliverables

**Build an end-to-end prototype and deploy it to a local endpoint**

**Live Demo:** house-whisperer.vercel.app

---

## Task 5: Creating a Golden Test Data Set

### ✅ Deliverables

**Assess your pipeline using the RAGAS framework including key metrics faithfulness, response relevance, context precision, and context recall. Provide a table of your output results.**

### ✅ RAG Evaluation Summary (Key Metrics)

**📊 Naive Scores:**

| Metric | Score | Description |
|--------|-------|-------------|
| **Context Precision** | 0.4039 | Moderate, includes some irrelevant content |
| **Response Relevancy** | 0.6189 | Fairly good, responses generally on-topic |
| **Faithfulness** | 0.5758 | Moderate, some hallucination risk |
| **Context Recall** | 0.4667 | Retrieves about half of needed context |
| **🎯 Overall Score** | **0.5163** | Passable baseline |

**Performance Metrics:**
- **Tokens:** 239,054
- **Latency:** 40.36s

**What conclusions can you draw about the performance and effectiveness of your pipeline with this information?**

### ✅ Key Metrics Recap

**Context Precision: 0.4039**
- Measures how much of the retrieved context is relevant to the question.
- A moderate score, indicating the retriever is including a fair amount of noise or tangential content.

**Response Relevancy: 0.6189**
- Measures how well the generated responses align with the user's question.
- A fairly good score responses are generally on-topic, though not always deeply informative or accurate.

**Faithfulness: 0.5758**
- Measures how grounded the response is in the retrieved documents.
- A moderate score suggests that while hallucination risk is present, over half of the responses are reasonably supported by the context.

**Context Recall: 0.4667**
- Indicates how much of the ground truth context is retrieved.
- Moderate about half of the important context is retrieved, which limits completeness of responses.

**Overall Score: 0.5163**
- A composite score of response quality and retrieval performance.
- This is a passable baseline but underwhelming compared to more advanced strategies.

**Tokens: 239,054 | Latency: 40.36s**
- Moderate token usage and latency not highly efficient, but manageable depending on use case.

### 🎯 Conclusions

**Balanced but Unremarkable**
- Naive RAG offers moderate performance across all core metrics. The model is capable of producing coherent, somewhat accurate answers but lacks depth and full factual grounding.

**Limitations in Context Retrieval**
- Context Recall (0.4667) and Context Precision (0.4039) show that this approach neither captures all important context nor filters irrelevant content well. This results in partial answers and noise exposure.

**Moderate Faithfulness with No Reranking**
- Faithfulness at 0.5758 is not terrible, but indicates the model is still vulnerable to hallucination due to imperfect retrieval. This is expected, since Naive RAG likely uses basic top-k dense retrieval with no reranking or compression.

**Latency and Cost**
- With over 239k tokens and ~40s latency, the pipeline is not cheap or fast, yet the quality isn't high enough to justify the cost in most production contexts.

---

## Task 6: The Benefits of Advanced Retrieval

### ✅ Deliverables

**Describe the retrieval techniques that you plan to try and to assess in your application. Write one sentence on why you believe each technique will be useful for your use case.**

| Technique | Description | Use Case Rationale |
|-----------|-------------|-------------------|
| **Naive Retrieval** | Retrieves top-k documents based purely on dense embedding similarity. | Useful because it's simple, fast, and sets a strong baseline for evaluating semantic search performance. |
| **BM25** | Uses traditional keyword-based scoring to rank documents based on term frequency and inverse document frequency | Useful for matching exact terms and short queries, especially when domain-specific keywords are used. |
| **Contextual Compression** | Ranks and filters dense retrieval results to remove irrelevant or low-signal content before passing to the LLM. | Useful because it reduces noise and improves answer faithfulness when documents contain lengthy or tangential content. |
| **Multi-Query Retrieval** | Expands the original query into multiple paraphrased or focused sub-queries to increase recall. | Useful for capturing diverse contexts and edge cases where a single query might miss relevant information. |
| **Ensemble Retrieval** | Combines dense, keyword, and/or reranked results to maximize both precision and recall. | Useful for balancing relevance, diversity, and completeness. Critical in regulated domains like home inspection. |

**Test a host of advanced retrieval techniques on your application.**

---

## Task 7: Assessing Performance

### ✅ Deliverables

**How does the performance compare to your original RAG application? Test the fine-tuned embedding model using the RAGAS frameworks to quantify any improvements. Provide results in a table.**

### 📋 DETAILED RAG PIPELINE RESULTS:

| Pipeline | Ctx Precision | Relevancy | Faithfulness | Ctx Recall | Overall | Tokens | Latency |
|----------|---------------|-----------|--------------|------------|---------|--------|---------|
| **Naive** | 0.4039 | 0.6189 | 0.5758 | 0.4667 | 0.5163 | 239,054 | 40.36 s |
| **MultiQuery** | 0.4873 | 0.6209 | 0.6281 | 0.4636 | 0.5500 | 318,059 | 51.79 s |
| **ContextualCompression** | 0.5909 | 0.6193 | 0.6136 | 0.2909 | 0.5287 | 107,158 | 35.54 s |
| **BM25** | 0.0000 | 0.0000 | 0.0000 | 0.1818 | 0.0455 | 254,369 | 31.47 s |
| **Ensemble** | 0.1887 | 0.6193 | 0.6177 | 0.5576 | 0.4958 | 307,782 | 41.55 s |

### 📊 Analysis of RAG pipeline results

### 🏁 Final Analysis

**🥇 Best Overall Performance: MultiQuery**
- Highest overall score (0.5500).
- Balanced across all metrics: solid context recall, highest faithfulness, and good response relevancy.
- Downside: highest token usage and latency → may require optimization or batching to be production-ready.
- ✅ Best for high-quality answers when trustworthiness and completeness are important.

**🥈 Most Efficient: ContextualCompression**
- Highest Context Precision (0.5909) → retrieves very relevant context.
- Low Context Recall (0.2909) → doesn't get much breadth, but what it gets is clean.
- Good Faithfulness (0.6136) and low tokens (107K) → very efficient pipeline.
- Lowest latency in the set.
- ✅ Best if you want to reduce cost/latency while preserving good response quality and faithfulness.

**🥉 Ensemble: Strong Recall, Weak Precision**
- Best Context Recall (0.5576) → pulls in the most ground-truth context.
- But very low Context Precision (0.1887) → includes lots of irrelevant or noisy chunks.
- Faithfulness and relevancy are good, but worse than MultiQuery and less efficient than ContextualCompression.
- ⚠️ Works best when paired with a reranker (like ContextualCompression) to clean noisy input.

**❌ BM25: Fails Completely**
- All generation metrics are 0.
- Retrieval is too weak to provide useful input.
- Avoid BM25 alone.

**🤔 Naive: Decent Baseline, Nothing Special**
- Balanced but average across the board.
- Relevancy and faithfulness are acceptable, but not best in class.
- Can serve as a fallback strategy.

**Articulate the changes that you expect to make to your app in the second half of the course. How will you improve your application?**

### 🔧 Planned Improvements to the Home Inspection App

Based on our midterm evaluation and available time, we plan two focused improvements:

**1. Complete the Inspector Voice-to-Report Pipeline**
- Integrate OpenAI Whisper API for voice transcription
- Implement basic report generation from voice notes
- This addresses our primary use case: helping inspectors save time

**2. Optimize Retrieval Performance**
- Test MultiQuery retrieval to improve response accuracy
- Fine-tune chunk size based on RAGAS metrics
- Focus on measurable improvements to response quality

If time permits, we'll add basic usage logging to gather insights for future iterations.

---

## Task 8: Documentation

**Loom video:** https://www.loom.com/share/be67715de9874e7aa418f83e3eee595b
---

*This certification challenge demonstrates the development of an AI-powered assistant for home inspectors, showcasing advanced RAG techniques, comprehensive evaluation, and practical application in a regulated professional domain.* 
