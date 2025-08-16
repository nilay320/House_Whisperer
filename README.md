# House Whisperer - AI Engineering Midterm Submission

## NC Home Inspector AI Assistant

A multi-agent RAG system that helps home buyers understand inspection reports by combining regulatory standards with real-time web information.

## 🎯 Problem Statement

Home buyers receive 30+ page technical inspection reports filled with jargon they don't understand, leading to confusion and poor decision-making during the largest purchase of their lives.

## 💡 Solution

An AI-powered chatbot that provides plain-English explanations of inspection findings by searching both:
- Pre-indexed NC inspection standards (InterNACHI, NCHILB, Building Codes)
- Real-time web search for recalls, manufacturers, and current best practices

## 🏗️ Architecture

### Multi-Agent System (LangGraph)
1. **Supervisor Agent** - Routes queries based on content analysis
2. **Research Agent** - Searches vector database (Qdrant)
3. **Web Search Agent** - Queries external sources (Tavily API)
4. **Synthesis Agent** - Generates comprehensive responses (GPT-4o-mini)

### Tech Stack
- **Frontend**: React + Tailwind CSS (Vercel)
- **Backend**: FastAPI + Python (Railway)
- **Vector DB**: Qdrant Cloud
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: text-embedding-3-small
- **Web Search**: Tavily API

## 🌐 Live Demo

The application is deployed and available at: https://house-whisperer.vercel.app/

## 🚀 If you want to run locally instead, 

### Prerequisites
- Node.js 18+
- Python 3.9+
- OpenAI API key
- Qdrant Cloud account
- Tavily API key

### 1. Clone the Repository
```bash
git clone https://github.com/rchallapilla/House_Whisperer.git
cd House_Whisperer
```

### 2. Backend Setup
```bash
cd api
pip install -r requirements.txt

# Create .env file with your credentials
cat > .env << EOF
OPENAI_API_KEY=your-openai-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-key
TAVILY_API_KEY=your-tavily-key
EOF

# Run the API server
python app.py
# API will be available at http://localhost:8000
```

### 3. Frontend Setup (in new terminal)
```bash
cd frontend
npm install

# Set API URL to local backend
echo "REACT_APP_API_URL=http://localhost:8000" > .env.development

# Start the React app
npm start
# App will open at http://localhost:3000
```

### 4. Test the Application
- Open http://localhost:3000 in your browser
- Try asking questions like:
  - "What are the electrical inspection requirements in NC?"
  - "Are there any recalls on Rheem water heaters?"
  - "How do I inspect HVAC systems?"

## 📊 Key Features

- **Intelligent Query Routing**: Automatically determines if web search is needed
- **Source Attribution**: Shows relevance scores and source types
- **Real-time Streaming**: SSE for progress updates during search
- **Fallback Strategies**: Web search when RAG returns no results

### Batch runner
- `scripts/run_batch_questions_chat_eval.py` supports `--print-config` to print masked backend config and embeds it into the run’s JSONL/Markdown outputs for traceability.

### Inspector RAG flow
- Default behavior: single pass — `RAG → optional Web → Synthesis`.
- Web augmentation can run once when RAG is empty, or when `USE_WEB_AUGMENT=1` and the query matches keywords.
- Implemented in `api/langgraph_inspector_rag.py` (nodes: `policy_node`, `rag_tool_node`, `web_tool_node`, `synthesis_node`).

## 🔍 Example Queries

- "What are the electrical inspection requirements in NC?"
- "Are there any recalls on Rheem water heaters?"
- "What's the latest on AFCI requirements?"
- "How do I inspect HVAC systems?"

## 📁 Project Structure

```
House_Whisperer/
├── api/
│   ├── app.py                    # FastAPI server
│   ├── langgraph_inspector_rag.py # Multi-agent workflow
│   └── web_search_tools.py       # Tavily integration
├── frontend/
│   └── src/
│       └── components/
│           └── ChatbotWidget.js  # Chat interface
└── docs/
    └── data/                     # Indexed documents
```

## 🎓 Midterm Deliverables

This project satisfies all certification requirements:
- ✅ Multi-agent architecture with LangGraph
- ✅ External API integration (Tavily)
- ✅ Agentic reasoning through intelligent routing
- ✅ Production deployment (Vercel + Railway)
