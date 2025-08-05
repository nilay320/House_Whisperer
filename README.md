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

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- OpenAI API key
- Qdrant Cloud account
- Tavily API key

### Backend Setup
```bash
cd api
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
export QDRANT_URL="your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"
export TAVILY_API_KEY="your-tavily-key"

# Run the API
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install

# Set API URL in .env.development
echo "REACT_APP_API_URL=http://localhost:8000" > .env.development

# Start the app
npm start
```

## 📊 Key Features

- **Intelligent Query Routing**: Automatically determines if web search is needed
- **Source Attribution**: Shows relevance scores and source types
- **Real-time Streaming**: SSE for progress updates during search
- **Fallback Strategies**: Web search when RAG returns no results

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

## 🔗 Links

- [Assignment Requirements](docs/midterm/requirements.txt)
- [Project Plan](AI_ENGINEERING_PROJECT_PLAN.md)