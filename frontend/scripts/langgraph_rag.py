#!/usr/bin/env python3
"""LangGraph-based RAG system with RecursiveCharacterTextSplitter for NC Inspector AI."""

import os
import json
from typing import Dict, List, Any, TypedDict
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Configuration
COLLECTION_NAME = 'inspector-standards'
EMBEDDING_MODEL = 'text-embedding-3-small'
CHAT_MODEL = 'gpt-4o-mini'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Initialize clients (defer LLM initialization to avoid pydantic issues)
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
)

# Initialize text splitter with consistent settings
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n", "\n", ". ", ".", " ", ""]
)

# Define state for LangGraph
class RAGState(TypedDict):
    query: str
    retrieved_docs: List[Document]
    context: str
    sources: List[Dict[str, Any]]
    response: str
    error: str

def initialize_vector_store():
    """Initialize Qdrant vector store with LangChain integration."""
    # Check if collection exists, create if not
    try:
        qdrant_client.get_collection(COLLECTION_NAME)
        print(f"✅ Using existing collection: {COLLECTION_NAME}")
    except Exception:
        print(f"📋 Creating new collection: {COLLECTION_NAME}")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
    
    # Initialize LangChain vector store
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )
    
    return vector_store

def retrieval_node(state: RAGState) -> RAGState:
    """Retrieve relevant documents for the query."""
    print(f"🔍 Retrieving documents for: {state['query']}")
    
    try:
        vector_store = initialize_vector_store()
        
        # Retrieve similar documents
        retrieved_docs = vector_store.similarity_search_with_score(
            state['query'], 
            k=5
        )
        
        # Extract documents and scores
        docs = []
        sources = []
        
        for doc, score in retrieved_docs:
            docs.append(doc)
            sources.append({
                "source": doc.metadata.get("source", "Unknown"),
                "score": float(score),
                "content": doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
            })
        
        print(f"📋 Retrieved {len(docs)} documents")
        for i, source in enumerate(sources):
            print(f"   [{i+1}] {source['source']} (score: {source['score']:.4f})")
        
        return {
            **state,
            "retrieved_docs": docs,
            "sources": sources
        }
        
    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        return {
            **state,
            "error": f"Retrieval failed: {str(e)}"
        }

def context_preparation_node(state: RAGState) -> RAGState:
    """Prepare context from retrieved documents."""
    print("📝 Preparing context from retrieved documents")
    
    try:
        if not state.get("retrieved_docs"):
            return {
                **state,
                "error": "No documents retrieved"
            }
        
        # Format context from retrieved documents
        context_parts = []
        for i, doc in enumerate(state["retrieved_docs"]):
            source = doc.metadata.get("source", "Unknown")
            content = doc.page_content
            context_parts.append(f"[{i+1}] {content}\nSource: {source}")
        
        context = "\n\n".join(context_parts)
        
        print(f"✅ Prepared context: {len(context)} characters")
        
        return {
            **state,
            "context": context
        }
        
    except Exception as e:
        print(f"❌ Context preparation error: {e}")
        return {
            **state,
            "error": f"Context preparation failed: {str(e)}"
        }

def generation_node(state: RAGState) -> RAGState:
    """Generate response using retrieved context."""
    print("💭 Generating response with LLM")
    
    try:
        system_prompt = """You are an expert home inspector assistant with deep knowledge of InterNACHI standards, NCHILB regulations, and North Carolina building codes. 

Answer questions accurately based on the provided context from official inspection standards and regulations. Be specific and cite relevant details from the context when possible."""

        user_prompt = f"""Context from inspection standards:
{state['context']}

Question: {state['query']}

Provide a clear, accurate answer based on the context above. If the context doesn't contain enough information, say so clearly."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Generate response
        response = llm.invoke(messages)
        
        print(f"✅ Generated response: {len(response.content)} characters")
        
        return {
            **state,
            "response": response.content
        }
        
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return {
            **state,
            "error": f"Generation failed: {str(e)}"
        }

def create_rag_graph():
    """Create the LangGraph RAG workflow."""
    # Create the graph
    workflow = StateGraph(RAGState)
    
    # Add nodes
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("context_preparation", context_preparation_node)
    workflow.add_node("generation", generation_node)
    
    # Define the flow
    workflow.add_edge(START, "retrieval")
    workflow.add_edge("retrieval", "context_preparation")
    workflow.add_edge("context_preparation", "generation")
    workflow.add_edge("generation", END)
    
    # Add memory for conversation history
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    return app

def query_rag_system(query: str, thread_id: str = "default") -> Dict[str, Any]:
    """Query the LangGraph RAG system."""
    print(f"\n🚀 Starting LangGraph RAG query: {query}")
    
    # Create the RAG graph
    app = create_rag_graph()
    
    # Initial state
    initial_state = {
        "query": query,
        "retrieved_docs": [],
        "context": "",
        "sources": [],
        "response": "",
        "error": ""
    }
    
    # Run the graph
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Execute the workflow
        result = app.invoke(initial_state, config)
        
        if result.get("error"):
            return {
                "success": False,
                "error": result["error"],
                "query": query
            }
        
        return {
            "success": True,
            "query": query,
            "response": result["response"],
            "sources": result["sources"],
            "context_length": len(result.get("context", "")),
            "num_docs": len(result.get("retrieved_docs", []))
        }
        
    except Exception as e:
        print(f"❌ RAG system error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

def test_langgraph_rag():
    """Test the LangGraph RAG system."""
    print("🧪 Testing LangGraph RAG System\n")
    
    test_queries = [
        "What are the requirements for electrical inspections in North Carolina?",
        "How often should HVAC systems be inspected?",
        "What should I look for when inspecting a roof?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)}")
        print(f"{'='*60}")
        
        result = query_rag_system(query, thread_id=f"test_{i}")
        
        if result["success"]:
            print(f"\n✅ Query: {result['query']}")
            print(f"📊 Retrieved {result['num_docs']} documents")
            print(f"📝 Context length: {result['context_length']} characters")
            print(f"📚 Sources: {len(result['sources'])} unique sources")
            
            print(f"\n💭 Response:")
            print(f"{result['response']}")
            
            print(f"\n📚 Sources Used:")
            for j, source in enumerate(result['sources'], 1):
                print(f"   {j}. {source['source']} (score: {source['score']:.4f})")
        else:
            print(f"\n❌ Query failed: {result['error']}")
    
    print(f"\n🎉 LangGraph RAG testing completed!")

if __name__ == "__main__":
    test_langgraph_rag()