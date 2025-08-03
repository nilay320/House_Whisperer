# Testing Commands for Web Search Integration

## 1. Basic Test
```bash
cd api
python test_web_search.py
```

## 2. Debug Test (shows the actual response)
```bash
python test_debug.py
```

## 3. Test Specific Queries
```python
# Create a test file: test_specific.py
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend', '.env.local'))

from langgraph_inspector_rag import query_inspector_rag

# Test queries that should trigger different paths:

# 1. Should use vector DB only (no web search triggers)
result1 = query_inspector_rag("What are the electrical inspection requirements?")
print(f"Query 1 - Sources: {len(result1.get('sources', []))}")

# 2. Should trigger web search (has "latest" keyword)
result2 = query_inspector_rag("What are the latest best practices for roof inspection?")
print(f"Query 2 - Sources: {len(result2.get('sources', []))}")

# 3. Should trigger web search (has "recall" keyword)
result3 = query_inspector_rag("Are there any recalls on Zinsco panels?")
print(f"Query 3 - Sources: {len(result3.get('sources', []))}")
```

## 4. Check the Flow
Watch the console output for these decision points:
- "🤖 Supervisor decision: No research attempted yet -> research_agent"
- "🤖 Supervisor decision: Need web search -> web_search_agent"
- "🤖 Supervisor decision: Have results, no response -> synthesis_agent"

## 5. Frontend Test
```bash
# In one terminal:
cd frontend
npm run dev

# In another terminal:
cd api
python server.py

# Then test in the UI with queries like:
# - "What are the latest updates on Federal Pacific panels?"
# - "How to inspect HVAC systems"
```