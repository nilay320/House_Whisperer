# AI Engineering Project Plan - Home Inspector AI Assistant

## Project Overview

This document contains the complete project plan for the **Home Inspector AI Assistant** for the AI Engineering Bootcamp, including midterm and Demo Day requirements.

---

## Original Project Vision (From PDF)

### Problem Worth Solving
- Inspectors waste 3-5 hours per report manually writing and formatting
- Reports are 30+ pages long, filled with jargon buyers don't understand  
- Missed upsell opportunities for agents and post-inspection services

### Refined Solution Scope
**A. Inspector Side - Report Writer**
- Mobile-first voice/photo capture → LLM auto-generates structured reports
- Template tuning for InterNACHI/ASHI formats
- "Defect library" ingestion improves consistency

**B. Buyer Side - Report Explainer Bot**
- Personalized Q&A agent trained on the report ("Explain the roof risk in plain English")
- Optional upsells: schedule contractors, get quotes, auto-summarized punch list

### Target Personas
| Persona | Pain Point | How We Solve It |
|---------|------------|-----------------|
| Solo Inspector | Wasted time, burnout | Voice-to-report saves 60% of time |
| Inspection Firm Owner | Staff report quality varies | Standardized output from templates |
| Home Buyer | Confusion & anxiety | Q&A bot makes report digestible |
| Real Estate Agent | Lost post-inspection momentum | White-label chatbot adds buyer value |

---

## Midterm Requirements (Certification Challenge)

### Overview
- **Due:** February 25, 4:00 PM PT
- **Format:** AI Product Management + AI Engineering
- **Deliverables:** Problem/Solution definition, RAG prototype, evaluation, fine-tuning
- **Goal:** Build foundation for Demo Day project

### Task Breakdown

#### Task 1: Problem and Audience
- 1-sentence problem description
- 1-2 paragraphs on why it's a problem for specific user
- Create list of potential user questions

#### Task 2: Propose Solution
- 1-2 paragraphs on proposed solution
- Describe tools for each part of stack:
  - LLM, Embedding Model, Orchestration, Vector Database
  - Monitoring, Evaluation, User Interface, Serving & Inference
- Where will you use agents/agentic reasoning?

#### Task 3: Data Sources
- Describe all data sources and external APIs
- Describe default chunking strategy and reasoning
- Optional: specific data for other parts of application

#### Task 4: End-to-End Prototype
- Build RAG application using open-source stack
- Deploy to Hugging Face Space (or other endpoint)

#### Task 5: Golden Test Data Set
- Generate synthetic test data set for RAGAS evaluation
- Assess pipeline using faithfulness, response relevance, context precision, context recall
- Provide table of results and conclusions

#### Task 6: Fine-Tuning Embeddings
- Generate synthetic fine-tuning data
- Fine-tune open-source embedding model
- Provide link to fine-tuned model on Hugging Face Hub

#### Task 7: Performance Assessment
- Compare performance of fine-tuned vs original RAG application
- Use RAGAS framework to quantify improvements
- Articulate expected changes for second half of course

#### Final Submission Requirements
- Public GitHub repo with:
  - 5-minute (OR LESS) Loom video demo
  - Written document addressing each deliverable
  - All relevant code
- Public application link (Hugging Face or other)
- Public link to fine-tuned embedding model

---

## Example Project Analysis (SERCH Chatbot)

### What They Built
- **Problem:** People don't understand AI industry evolution
- **Solution:** Chatbot for internal stakeholders to ask questions about AI technology
- **Data:** Simon Willison's blog posts
- **Stack:** GPT-4o-mini, text-embedding-3-small, LangGraph, Qdrant, LangSmith, RAGAS, Streamlit, Hugging Face

### Key Metrics (Before/After Fine-tuning)
| Metric | Before | After |
|--------|--------|-------|
| Context Recall | 0.1926 | 0.2669 |
| Faithfulness | 0.3870 | 0.5346 |
| Factual Correctness | 0.3575 | 0.4217 |
| Answer Relevancy | 0.8723 | 0.8698 |
| Context Entity Recall | 0.2739 | 0.3179 |

---

## Current Project Status

### ✅ Completed Features
- React frontend with role-based authentication (Inspector/Buyer)
- Voice recording infrastructure with microphone access
- Photo capture capabilities
- AI chatbot for buyers with PDF upload capability
- OpenAI API integration with streaming responses
- 2-tab authentication system (Sign In/Create Account)
- Deployed to Vercel with PWA-ready manifest

### 🔄 In Progress Features
- Voice-to-text transcription pipeline
- Firestore database integration for transcriptions
- Report generation from voice notes

### ❌ Missing for Midterm
- Vector database for semantic search (Buyer Q&A)
- Proper RAG pipeline (currently using mock responses)
- RAGAS evaluation framework
- Fine-tuned embeddings
- Golden test dataset
- Performance metrics

---

## Proposed Midterm Submission Strategy

### **Project Title:** "Inspector AI - Home Inspection Report Assistant"

### **Task 1: Problem and Audience**

**Problem (1 sentence):** 
Home buyers receive 30+ page technical inspection reports filled with jargon they don't understand, leading to confusion and poor decision-making during the largest purchase of their lives.

**Why it's a problem (1-2 paragraphs):**
Home buyers are typically non-technical individuals making a $300K+ purchase decision based on inspection reports they can't interpret. They ask questions like "Is this electrical issue serious?" or "How much will roof repairs cost?" but get no immediate answers. This leads to delayed decisions, unnecessary anxiety, and sometimes walking away from good properties or proceeding with bad ones. Real estate agents can't answer technical questions, and calling inspectors for clarification creates delays in fast-moving markets.

**User Questions They Ask:**
- "What are the most critical issues I should address first?"
- "How much might these repairs cost?"
- "Are there any safety concerns I should know about?"
- "What maintenance should I prioritize in the first year?"
- "Are there any deal-breakers in this report?"

**Primary User:** Home buyers
**Secondary User:** Real estate agents

### **Task 2: Solution Stack**

**Solution:** 
An AI-powered chatbot that ingests inspection report PDFs and provides plain-English explanations, cost estimates, and prioritized recommendations through conversational Q&A. The system transforms technical jargon into actionable insights, helping buyers make informed decisions quickly.

**Tech Stack:**
- **LLM:** GPT-4o-mini (cost-effective, excellent for Q&A and explanation tasks)
- **Embedding:** text-embedding-3-small → fine-tune snowflake-arctic-embed-l
- **Orchestration:** LangChain (flexible, good ecosystem integration)
- **Vector Database:** Pinecone or Qdrant (semantic search of report sections)
- **Monitoring:** LangSmith (LLM ops and tracing)
- **Evaluation:** RAGAS (RAG-specific metrics)
- **UI:** React (already implemented, professional interface)
- **Serving:** Vercel (fast deployment, good performance)

**Agent Usage:** 
Agentic reasoning for:
1. Cost estimation queries (search current repair costs via APIs)
2. Follow-up question generation based on user concerns
3. Risk prioritization based on safety vs cosmetic issues

### **Task 3: Data Sources**

**Primary Data Sources:**
1. **Sample Inspection Reports:** 10-15 real PDF inspection reports covering various property types
2. **Industry Standards:** InterNACHI and ASHI inspection standards for grounding and consistency
3. **Repair Cost Data:** HomeAdvisor/Angi/Fixr cost databases for accurate estimates

**External APIs:**
1. **Tavily Search:** For current/local repair costs and contractor information
2. **OpenAI Whisper:** (Future feature) Voice questions from mobile users
3. **Real Estate APIs:** Property value context for repair cost-benefit analysis

**Chunking Strategy:** 
Section-based chunking by inspection category (HVAC, Electrical, Plumbing, Structural, etc.) rather than character-based chunking. This approach respects the natural semantic boundaries in inspection reports and improves retrieval accuracy for category-specific questions.

**Reasoning:** Inspection reports have clear categorical structure. Users typically ask questions about specific systems ("What's wrong with the electrical?") rather than general queries, making section-based chunking more effective than arbitrary character splits.

### **Task 4: Implementation Focus for Midterm**

**Strategic Decision:** Focus on the **Buyer Q&A RAG component** rather than the inspector voice-to-text pipeline for the midterm submission.

**Why:** This aligns better with traditional RAG evaluation frameworks and leverages existing infrastructure (ChatbotWidget with PDF upload is already 80% complete).

**Implementation Plan:**
1. Replace mock responses with proper RAG pipeline
2. Implement vector database for semantic search  
3. Connect to existing PDF processing capabilities
4. Add structured response formatting for repair costs and priorities

### **Task 5: Golden Dataset Creation**

**Synthetic Test Questions:**
- "What are the most serious issues in this report?"
- "How much will the electrical problems cost to fix?"  
- "Are there any safety concerns I should know about immediately?"
- "Should I walk away from this property?"
- "What repairs should I prioritize in the first year?"
- "Explain the HVAC issues in simple terms"
- "Is the roof problem expensive to fix?"
- "What does 'needs immediate attention' mean for the plumbing?"

**Question Categories:**
- Cost estimation (25%)
- Risk assessment (25%) 
- Technical explanation (25%)
- Decision support (25%)

### **Tasks 6-7: Fine-tuning & Evaluation Strategy**

**Fine-tuning Focus:** 
Optimize embeddings for inspection terminology and home repair vocabulary to improve retrieval accuracy for domain-specific queries.

**Expected Improvements:**
- Better matching of technical terms with plain-English questions
- Improved context recall for multi-system issues
- Enhanced accuracy for cost-related queries

---

## Demo Day Enhancement Strategy

### **Midterm → Demo Day Evolution**

**Midterm Scope:** Buyer Q&A RAG system (single-sided)
**Demo Day Scope:** Full dual-sided platform (Buyers + Inspectors)

### **Demo Day Additions:**
1. **Inspector Voice-to-Text Pipeline:**
   - Voice recording → Whisper transcription → GPT-4 report generation
   - Mobile-optimized PWA for field use
   - Structured report templates (ASHI/InterNACHI compliant)

2. **Advanced Features:**
   - Photo analysis with GPT-4 Vision
   - Automated cost estimation integration
   - Contractor referral system
   - Multi-property comparison tools

3. **Business Case:**
   - ROI calculations for inspectors (time savings)
   - Market expansion potential (dual-sided network effects)
   - Revenue model demonstration (SaaS + transaction fees)

### **Strategic Advantage**

**Why This Project is Stronger Than Examples:**
- **Real Business Value:** Solves actual $300K+ decisions vs academic research
- **Clear User Personas:** Home buyers are a well-defined, addressable market
- **Working Infrastructure:** Already have deployed, functional prototype
- **Dual-Sided Potential:** Both buyers AND inspectors benefit (network effects)
- **Market Timing:** AI adoption in real estate is accelerating
- **Measurable Impact:** Time savings and decision accuracy are quantifiable

---

## Technical Architecture Decisions

### **Voice-to-Text-to-Database Pipeline:**
```
Voice Recording → Firebase Storage (audio files)
       ↓
Whisper API → Transcription (text)
       ↓  
Firestore → Save transcription + audio URL reference
       ↓
Report Generation → Query transcriptions from Firestore
       ↓
GPT-4 Functions → Structured inspection data
       ↓
PDF Generation → Professional inspection reports
```

### **Buyer Q&A RAG Pipeline:**
```
PDF Upload → Text Extraction
       ↓
Chunking → Section-based (by inspection category)
       ↓
Embeddings → Vector Storage (Pinecone/Qdrant)
       ↓
User Question → Semantic Search → Relevant Contexts
       ↓
GPT-4 + Context → Plain-English Answer + Cost Estimates
```

### **Database Architecture:**
```
Firestore Collections:
├── inspections/ (metadata, inspector info, property details)
├── voiceNotes/ (transcriptions, audio URLs, timestamps)
├── photos/ (image URLs, AI descriptions, timestamps)
├── generatedReports/ (report content, PDF URLs)
└── conversations/ (buyer Q&A history, feedback)

Firebase Storage:
├── audio/ (voice recordings)
├── photos/ (inspection images)  
└── reports/ (generated PDFs)

Vector Database (Pinecone/Qdrant):
├── report_embeddings (chunked report sections)
└── conversation_history (for personalization)
```

---

## Next Steps

### **Immediate Actions (Midterm Prep):**
1. ✅ **Test existing PDF upload functionality** 
2. **Implement vector database integration** (Pinecone or Qdrant)
3. **Replace mock responses with RAG pipeline**
4. **Create golden test dataset** (synthetic Q&A pairs)
5. **Implement RAGAS evaluation framework**
6. **Fine-tune embedding model** on inspection terminology
7. **Deploy to Hugging Face Space**
8. **Record demo video** (5 minutes max)

### **Timeline (Next 2 Weeks):**
- **Week 1:** RAG pipeline implementation + evaluation setup
- **Week 2:** Fine-tuning + performance testing + documentation

### **Demo Day Preparation (After Midterm):**
1. **Voice-to-text integration** with Whisper API
2. **Inspector mobile interface** optimization
3. **Advanced agentic features** (cost estimation, contractor referrals)
4. **Business model validation** and market research
5. **Scale testing** with real inspection reports

---

## Success Metrics

### **Midterm Success Criteria:**
- **Functional RAG pipeline** with real inspection report processing
- **RAGAS scores** showing measurable improvement after fine-tuning
- **User-friendly interface** demonstrating clear value proposition
- **Technical documentation** showing mastery of AI engineering concepts

### **Demo Day Success Criteria:**
- **Full dual-sided platform** serving both inspectors and buyers
- **Quantified business impact** (time savings, decision accuracy)
- **Market validation** through user testing and feedback
- **Scalable architecture** ready for real-world deployment

---

*This document serves as the complete project plan and context for the Home Inspector AI Assistant. It can be referenced throughout development to maintain alignment with course requirements and project vision.*