# PROJECT CONTEXT - House Whisperer Midterm Submission

## Current Implementation Status (Midterm Branch)

### ✅ Completed Features
1. **Multi-Agent RAG System with LangGraph**
   - Supervisor agent for intelligent query routing
   - Research agent for vector database search (Qdrant)
   - Web search agent for real-time information (Tavily API)
   - Synthesis agent for response generation (GPT-4o-mini)

2. **External API Integration**
   - Tavily web search for recalls, manufacturers, and current practices
   - Trusted domain filtering for quality results
   - Fallback strategies when RAG returns no results

3. **Frontend Application**
   - React-based chat interface deployed on Vercel
   - Real-time SSE streaming for progress updates
   - Source attribution with relevance scores
   - Mobile-responsive design

4. **Backend API**
   - FastAPI backend deployed on Railway
   - Server-Sent Events (SSE) for streaming responses
   - CORS configuration for Vercel integration
   - Health check and debugging endpoints

### 🔧 Technology Stack
- **LLM**: GPT-4o-mini
- **Embeddings**: text-embedding-3-small
- **Orchestration**: LangGraph
- **Vector DB**: Qdrant Cloud
- **Web Search**: Tavily API
- **Frontend**: React + Tailwind CSS
- **Backend**: FastAPI + Python
- **Deployment**: Vercel (frontend) + Railway (backend)

### 📁 Key Files
- `api/langgraph_inspector_rag.py` - Multi-agent workflow implementation
- `api/web_search_tools.py` - Tavily web search integration
- `api/app.py` - FastAPI server with SSE streaming
- `frontend/src/components/ChatbotWidget.js` - Chat interface
- `docs/midterm/requirements.txt` - Assignment requirements

### 🌐 Deployment URLs
- Frontend: Deployed on Vercel
- Backend API: Deployed on Railway with environment variables

### 📊 Data Sources
- Pre-indexed NC inspection standards in Qdrant
- InterNACHI Standards of Practice
- NCHILB regulations
- NC Building Codes (2024)
- Real-time web search via Tavily

### 🚀 Next Steps (Demo Day)
1. Complete voice-to-report pipeline with Whisper API
2. Optimize retrieval with MultiQuery
3. Add basic usage monitoring

### ⚠️ Important Notes
- Firebase authentication removed for midterm (not required)
- Mobile app components removed (focus on web RAG)
- Using direct tool calls instead of ReAct agents for performance
- All environment variables must be set in deployment platforms

## Recent Changes (Midterm Submission)
- Added Tavily web search integration for external API requirement
- Implemented multi-agent routing with fallback strategies
- Deployed to production (Vercel + Railway)
- Removed Firebase dependencies
- Optimized for performance with direct tool calls