#!/usr/bin/env python3
"""Multi-Agent LangGraph RAG System for NC Inspector AI following the notebook pattern."""

import os
import json
from typing import Dict, List, Any, TypedDict, Literal
from operator import add
from dotenv import load_dotenv

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

# Qdrant client
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()

# Configuration
COLLECTION_NAME = 'inspector-standards'
EMBEDDING_MODEL = 'text-embedding-3-small'
CHAT_MODEL = 'gpt-4o-mini'

# Strip whitespace from environment variables on module load
for key in ['OPENAI_API_KEY', 'QDRANT_URL', 'QDRANT_API_KEY']:
    value = os.environ.get(key)
    if value:
        os.environ[key] = value.strip()
        print(f"✅ Stripped whitespace from {key}")

# Initialize clients (will be done inside functions to avoid import-time errors)
embeddings = None
llm = None
qdrant_client = None

def _initialize_clients():
    """Initialize clients if not already done."""
    global embeddings, llm, qdrant_client
    
    # Check environment variables first (as suggested by Claude UI debugging steps)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        openai_key = openai_key.strip()  # Strip whitespace
    if not openai_key:
        # Try loading from .env file as fallback
        from dotenv import load_dotenv
        load_dotenv()
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            openai_key = openai_key.strip()
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
    
    qdrant_url = os.environ.get("QDRANT_URL")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY")
    if qdrant_url:
        qdrant_url = qdrant_url.strip()  # Strip whitespace
    if qdrant_api_key:
        qdrant_api_key = qdrant_api_key.strip()  # Strip whitespace
    if not qdrant_url or not qdrant_api_key:
        raise ValueError("QDRANT_URL or QDRANT_API_KEY environment variables not set")
    
    print(f"✅ Environment variables checked - OpenAI key: {openai_key[:10]}...")
    
    if embeddings is None:
        # Fix Pydantic compatibility issue by properly setting up callbacks and rebuilding models
        try:
            # Import all required classes and types first
            from langchain_core.caches import BaseCache
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            from langchain_core.callbacks import BaseCallbackManager, Callbacks
            from langchain_core.callbacks.base import BaseCallbackHandler
            from typing import List, Optional, Union
            
            # Define the Callbacks type that Pydantic is looking for
            # This resolves the "name 'Callbacks' is not defined" error
            Callbacks = Union[List[BaseCallbackHandler], BaseCallbackManager, None]
            
            # Make sure the Callbacks type is available in the global namespace for model rebuild
            import sys
            current_module = sys.modules[__name__]
            setattr(current_module, 'Callbacks', Callbacks)
            
            # Define callbacks before model rebuild (as suggested by Claude UI)
            callbacks = []  # Empty callbacks list for now
            
            # Force model rebuilds in correct order with proper dependencies
            if hasattr(BaseCache, 'model_rebuild'):
                BaseCache.model_rebuild()
            if hasattr(BaseCallbackManager, 'model_rebuild'):
                BaseCallbackManager.model_rebuild()
            
            # Rebuild models now that dependencies are in place and Callbacks is defined
            OpenAIEmbeddings.model_rebuild()
            ChatOpenAI.model_rebuild()
            
            print("✅ Successfully rebuilt Pydantic models with callbacks")
        except Exception as e:
            print(f"⚠️  Warning: Could not rebuild models: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
        # Initialize with proper parameters (as suggested by Claude UI)
        try:
            # Use the already stripped openai_key from above
            embeddings = OpenAIEmbeddings(
                model=EMBEDDING_MODEL,
                openai_api_key=openai_key  # Use the stripped key
            )
            print(f"✅ OpenAI Embeddings initialized successfully with key: {openai_key[:10]}...")
        except Exception as e:
            print(f"❌ Failed to initialize embeddings: {e}")
            raise
            
    if llm is None:
        try:
            # Use the already stripped openai_key from above
            llm = ChatOpenAI(
                model=CHAT_MODEL,
                temperature=0.1,
                openai_api_key=openai_key,  # Use the stripped key
                callbacks=[],  # Explicit empty callbacks as suggested
                request_timeout=30,  # Add timeout for serverless
                max_retries=2  # Reduce retries for faster failure
            )
            print(f"✅ ChatOpenAI initialized successfully with key: {openai_key[:10]}...")
        except Exception as e:
            print(f"❌ Failed to initialize ChatOpenAI: {e}")
            raise
            
    if qdrant_client is None:
        try:
            # Get and validate Qdrant credentials (use the stripped versions from above)
            # qdrant_url and qdrant_api_key are already set and stripped above
            
            qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                timeout=30  # Add timeout for serverless
            )
            print(f"✅ Qdrant client initialized successfully - URL: {qdrant_url}")
        except Exception as e:
            print(f"❌ Failed to initialize Qdrant: {e}")
            raise

# Define the state following the notebook pattern
class InspectorRAGState(TypedDict):
    question: str
    context: List[Document]
    response: str
    inspector_sources: List[Dict[str, Any]]
    messages: List[BaseMessage]
    next_agent: str

# Initialize vector store connection to Qdrant Cloud
def get_vector_store():
    """Get the Qdrant vector store connection."""
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

# Tools for the agents
@tool
def search_inspector_standards(query: str) -> List[Dict[str, Any]]:
    """
    Search through NC inspector standards, regulations, and building codes.
    Use this for questions about home inspection requirements, standards, or regulations.
    """
    try:
        # Initialize clients if needed
        _initialize_clients()
        
        # Use direct Qdrant search to preserve metadata properly
        query_embedding = embeddings.embed_query(query)
        
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=5,
            with_payload=True
        )
        
        results = []
        for hit in search_result:
            # Extract metadata from Qdrant payload
            payload = hit.payload
            results.append({
                "content": payload.get("content", ""),
                "source": payload.get("source", "InterNACHI Standards of Practice"),  # Default fallback
                "category": payload.get("category", "Standards"),
                "score": float(hit.score),
                "document_name": payload.get("document_name", payload.get("source", "InterNACHI Standards of Practice"))
            })
            print(f"🔍 Retrieved: {payload.get('source', 'Unknown source')} (score: {hit.score:.3f})")
        
        return results
    except Exception as e:
        print(f"❌ Search error: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

@tool
def get_building_codes_info(query: str) -> List[Dict[str, Any]]:
    """
    Search specifically through NC Building Codes for construction and safety requirements.
    Use this for questions about building codes, construction standards, or safety regulations.
    """
    try:
        vector_store = get_vector_store()
        
        # Create a filter for building codes only
        docs_with_scores = vector_store.similarity_search_with_score(
            query, 
            k=3,
            filter={"category": "Building Codes"}
        )
        
        results = []
        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "score": float(score)
            })
        
        return results
    except Exception as e:
        return [{"error": f"Building codes search failed: {str(e)}"}]

# Agent definitions following the notebook pattern
def create_research_agent():
    """Create the research agent for inspector standards."""
    system_prompt = """You are a research agent specializing in North Carolina home inspection standards and regulations.

Your role:
- Search through inspector standards, building codes, and regulations
- Provide accurate, detailed information about inspection requirements
- Focus on InterNACHI standards, NCHILB regulations, and NC building codes
- Always cite your sources and provide specific details

Use the available tools to search for relevant information. Be thorough and accurate."""

    research_agent = create_react_agent(
        llm, 
        [search_inspector_standards, get_building_codes_info],
        state_modifier=system_prompt
    )
    
    return research_agent

def create_synthesis_agent():
    """Create the synthesis agent to compile and format responses."""
    system_prompt = """You are a synthesis agent that creates comprehensive, well-formatted responses about NC home inspection topics.

Your role:
- Take research findings and synthesize them into clear, actionable answers
- Organize information logically (requirements, standards, procedures, etc.)
- Ensure accuracy and completeness
- Format responses professionally for home inspectors
- Always include source attributions

Create responses that are practical and useful for working home inspectors."""

    synthesis_agent = create_react_agent(
        llm,
        [],  # No tools needed for synthesis
        state_modifier=system_prompt
    )
    
    return synthesis_agent

# Supervisor agent following the notebook pattern
def supervisor_node(state: InspectorRAGState) -> InspectorRAGState:
    """Supervisor that routes between research and synthesis agents."""
    
    print(f"🎯 Supervisor analyzing state:")
    print(f"   - Question: {state.get('question', 'None')}")
    print(f"   - Context: {len(state.get('context', []))} docs")
    print(f"   - Response: {len(state.get('response', ''))} chars")
    print(f"   - Current next_agent: {state.get('next_agent', 'None')}")
    
    supervisor_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a supervisor managing a team of AI agents to answer home inspection questions.

Team members:
- research_agent: Searches standards, regulations, and building codes
- synthesis_agent: Creates comprehensive responses from research

Your job is to determine which agent should act next based on the current state.

Rules:
- If no research has been done yet, choose 'research_agent'
- If research is complete but no final response exists, choose 'synthesis_agent' 
- If both research and synthesis are complete, choose 'FINISH'

Given the conversation below, who should act next?
Choose from: research_agent, synthesis_agent, FINISH"""),
        ("human", "Question: {question}\nCurrent context length: {context_length}\nCurrent response: {response}")
    ])
    
    try:
        context_length = len(state.get("context", []))
        response = state.get("response", "")
        
        # First check if agents have already set next_agent (respect agent signals)
        if state.get("next_agent") and state.get("next_agent") != "":
            next_agent = state.get("next_agent")
            print(f"🤖 Supervisor using agent signal: {next_agent}")
        else:
            # Use simple logic instead of LLM for more predictable routing
            print("🤖 Supervisor using logic-based routing...")
            
            # If no context, we need research
            if not state.get("context") or len(state.get("context", [])) == 0:
                next_agent = "research_agent"
                print("🤖 Supervisor decision: No context -> research_agent")
            # If we have context but no response, we need synthesis
            elif not state.get("response") or len(state.get("response", "").strip()) == 0:
                next_agent = "synthesis_agent"
                print("🤖 Supervisor decision: Have context, no response -> synthesis_agent")
            # If we have both context and response, we're done
            else:
                next_agent = "FINISH"
                print("🤖 Supervisor decision: Have context and response -> FINISH")
        
        return {
            **state,
            "next_agent": next_agent
        }
        
    except Exception as e:
        print(f"Supervisor error: {e}")
        return {
            **state,
            "next_agent": "research_agent"  # Default fallback
        }

def research_node(state: InspectorRAGState) -> InspectorRAGState:
    """Research agent node - optimized for speed."""
    import time
    research_start = time.time()
    
    try:
        print(f"🔍 Fast research starting for: {state['question']}")
        
        # Ensure clients are initialized
        _initialize_clients()
        
        # Skip the slow react agent - call search directly
        search_start = time.time()
        search_results = search_inspector_standards(state["question"])
        search_time = time.time() - search_start
        print(f"🔍 Direct search completed in {search_time:.2f}s")
        
        # Convert search results to documents
        context_docs = []
        sources = []
        
        for result_item in search_results:
            if "error" not in result_item:
                doc = Document(
                    page_content=result_item["content"],
                    metadata={
                        "source": result_item["source"],
                        "category": result_item.get("category", "Unknown"),
                        "score": result_item["score"]
                    }
                )
                context_docs.append(doc)
                sources.append({
                    "source": result_item["source"],
                    "score": result_item["score"]
                })
        
        # Signal that research is complete and synthesis should begin
        total_research_time = time.time() - research_start
        print(f"🔍 Fast research complete: Found {len(context_docs)} relevant documents in {total_research_time:.2f}s")
        
        return {
            **state,
            "context": context_docs,
            "inspector_sources": sources,
            "next_agent": "synthesis_agent"  # Tell supervisor to move to synthesis
        }
        
    except Exception as e:
        print(f"Research error: {e}")
        return {
            **state,
            "context": [],
            "inspector_sources": []
        }

def synthesis_node(state: InspectorRAGState) -> InspectorRAGState:
    """Synthesis agent node - optimized for speed."""
    import time
    synthesis_start = time.time()
    
    try:
        print(f"✍️ Fast synthesis starting...")
        
        # Ensure clients are initialized
        _initialize_clients()
        
        # Skip the slow react agent - use LLM directly
        context_text = "\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}"
            for doc in state.get("context", [])
        ])
        
        synthesis_prompt = f"""You are a North Carolina home inspection expert. Based on the following research about "{state['question']}":

{context_text}

Create a comprehensive, well-organized response that addresses the question thoroughly. Include specific requirements, standards, and procedures where applicable. Format your response professionally for working home inspectors."""

        # Use LLM directly instead of react agent
        llm_start = time.time()
        try:
            messages = [HumanMessage(content=synthesis_prompt)]
            response_message = llm.invoke(messages)
            llm_time = time.time() - llm_start
            print(f"✍️ Direct LLM call took {llm_time:.2f}s")
            
            response = response_message.content if hasattr(response_message, 'content') else str(response_message)
        except Exception as llm_error:
            # Try direct OpenAI client as fallback
            try:
                print(f"⚠️ LangChain failed, trying direct OpenAI client...")
                from openai import OpenAI
                api_key = os.environ.get("OPENAI_API_KEY", "").strip()
                if api_key:
                    client = OpenAI(api_key=api_key)
                    completion = client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=[{"role": "user", "content": synthesis_prompt}],
                        temperature=0.1
                    )
                    response = completion.choices[0].message.content
                    print(f"✅ Direct OpenAI client succeeded")
                else:
                    raise ValueError("No OpenAI API key available")
            except Exception as direct_error:
                import traceback
                print(f"❌ Both LangChain and direct OpenAI failed")
                print(f"❌ LangChain error: {llm_error}")
                print(f"❌ Direct error: {direct_error}")
                print(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Check if it's an API key issue
            if "api_key" in str(llm_error).lower() or "unauthorized" in str(llm_error).lower():
                response = "API key authentication error. Please check environment variables."
            elif "connection" in str(llm_error).lower() or "timeout" in str(llm_error).lower():
                # For connection errors, provide a useful response from the research
                response = f"Based on the research I found:\n\n{context_text[:1500]}\n\nNote: AI synthesis temporarily unavailable due to connection issues."
            else:
                response = f"I apologize, but I'm experiencing an error with the AI service ({type(llm_error).__name__}). However, based on the research I found:\n\n{context_text[:1000]}...\n\nError details: {str(llm_error)[:200]}"
        
        # Signal that synthesis is complete and workflow should finish
        total_synthesis_time = time.time() - synthesis_start
        print(f"✍️ Fast synthesis complete: Generated response ({len(response)} chars) in {total_synthesis_time:.2f}s")
        
        return {
            **state,
            "response": response,
            "next_agent": "FINISH"  # Tell supervisor to end the workflow
        }
        
    except Exception as e:
        print(f"Synthesis error: {e}")
        return {
            **state,
            "response": f"Error generating response: {str(e)}"
        }

def should_continue(state: InspectorRAGState) -> Literal["research_agent", "synthesis_agent", "__end__"]:
    """Determine the next step based on supervisor decision."""
    
    print(f"🎯 should_continue check:")
    print(f"   - Response exists: {bool(state.get('response') and len(state.get('response', '').strip()) > 0)}")
    print(f"   - Context exists: {bool(state.get('context') and len(state.get('context', [])) > 0)}")
    print(f"   - Next agent: {state.get('next_agent', 'None')}")
    
    # Safety check: if we already have a response, finish immediately
    if state.get("response") and len(state.get("response", "").strip()) > 0:
        print("🏁 Workflow ending: Response already generated")
        return "__end__"
    
    next_agent = state.get("next_agent", "research_agent")
    
    if next_agent == "FINISH":
        print("🏁 Workflow ending: Supervisor chose FINISH")
        return "__end__"
    elif next_agent == "research_agent":
        print("📚 Continuing to research_agent")
        return "research_agent"
    elif next_agent == "synthesis_agent":
        print("✍️ Continuing to synthesis_agent")
        return "synthesis_agent"
    else:
        # If no explicit next_agent is set and we have context but no response, go to synthesis
        if (state.get("context") and 
            len(state.get("context", [])) > 0 and 
            not (state.get("response") and len(state.get("response", "").strip()) > 0)):
            print("✍️ Auto-routing to synthesis_agent (have context, need response)")
            return "synthesis_agent"
        
        print("🏁 Workflow ending: Unknown next_agent or no clear path")
        return "__end__"

def create_inspector_rag_graph():
    """Create the multi-agent LangGraph workflow."""
    # Create the graph
    workflow = StateGraph(InspectorRAGState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_node)
    workflow.add_node("synthesis_agent", synthesis_node)
    
    # Add edges - start with supervisor
    workflow.add_edge(START, "supervisor")
    
    # Conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "research_agent": "research_agent",
            "synthesis_agent": "synthesis_agent",
            "__end__": END
        }
    )
    
    # Both agents return to supervisor
    workflow.add_edge("research_agent", "supervisor")
    workflow.add_edge("synthesis_agent", "supervisor")
    
    # Add memory
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    return app

async def query_inspector_rag_streaming(question: str, thread_id: str = "default"):
    """Query the multi-agent inspector RAG system with streaming updates."""
    import time
    
    # Initialize clients first
    _initialize_clients()
    
    print(f"🚀 Starting Multi-Agent Inspector RAG: {question}")
    setup_start = time.time()
    
    try:
        # Yield initial progress
        yield {"type": "progress", "message": "Setting up AI agents..."}
        
        # Create the graph
        app = create_inspector_rag_graph()
        setup_time = time.time() - setup_start
        print(f"⏱️ Graph setup took: {setup_time:.2f}s")
        
        # Initial state
        initial_state = {
            "question": question,
            "context": [],
            "response": "",
            "inspector_sources": [],
            "messages": [],
            "next_agent": ""
        }
        
        # Configuration
        config = {"configurable": {"thread_id": thread_id}}
        
        yield {"type": "progress", "message": "Starting research phase..."}
        workflow_start = time.time()
        
        # Run workflow step by step with progress updates
        step_count = 0
        max_steps = 10
        final_result = initial_state
        
        for step_output in app.stream(initial_state, config):
            step_start = time.time()
            step_count += 1
            print(f"🔄 Step {step_count}: {list(step_output.keys())}")
            
            # LangGraph returns dict with node name as key, state as value
            for node_name, state in step_output.items():
                node_elapsed = time.time() - step_start
                print(f"📝 Node '{node_name}' completed in {node_elapsed:.2f}s, state keys: {list(state.keys())}")
                
                # Update our tracking of the final result (always keep the latest state)
                final_result = state
                
                # Send progress updates based on which node is executing
                if node_name == "research_agent":
                    if "context" in state and len(state.get("context", [])) > 0:
                        context_count = len(state["context"])
                        yield {"type": "progress", "message": f"Found {context_count} relevant documents... ({node_elapsed:.1f}s)"}
                    else:
                        yield {"type": "progress", "message": "Searching through inspection standards..."}
                
                elif node_name == "synthesis_agent":
                    yield {"type": "progress", "message": f"Analyzing research and generating response... ({node_elapsed:.1f}s)"}
                
                elif node_name == "supervisor":
                    next_agent = state.get("next_agent", "")
                    if next_agent == "synthesis_agent":
                        yield {"type": "progress", "message": "Research complete, starting analysis..."}
                    elif next_agent == "FINISH":
                        yield {"type": "progress", "message": "Finalizing response..."}
            
            # Safety check for infinite loops
            if step_count >= max_steps:
                yield {"type": "progress", "message": "Workflow taking longer than expected, finalizing..."}
                break
        
        # After workflow completes, use the final accumulated state
        print(f"🏁 Workflow completed. Final result keys: {list(final_result.keys())}")
        print(f"🏁 Final response length: {len(final_result.get('response', ''))}")
        print(f"🏁 Final sources count: {len(final_result.get('inspector_sources', []))}")
        
        yield {
            "type": "complete",
            "response": final_result.get("response", "Workflow completed but no response generated."),
            "sources": final_result.get("inspector_sources", [])
        }
        
    except Exception as e:
        print(f"❌ Multi-agent RAG streaming error: {e}")
        yield {
            "type": "error",
            "message": f"RAG query failed: {str(e)}"
        }

def query_inspector_rag(question: str, thread_id: str = "default") -> Dict[str, Any]:
    """Query the multi-agent inspector RAG system."""
    # Initialize clients first
    _initialize_clients()
    
    print(f"🚀 Starting Multi-Agent Inspector RAG: {question}")
    
    # Create the graph with recursion limit
    app = create_inspector_rag_graph()
    
    # Configuration to prevent recursion issues
    config = {
        "recursion_limit": 10,  # Limit to 10 steps maximum
        "thread_id": thread_id
    }
    
    # Initial state
    initial_state = {
        "question": question,
        "context": [],
        "response": "",
        "inspector_sources": [],
        "messages": [],
        "next_agent": ""
    }
    
    # Run the workflow
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        result = app.invoke(initial_state, config)
        
        return {
            "success": True,
            "question": question,
            "response": result.get("response", "No response generated"),
            "sources": result.get("inspector_sources", []),
            "context_docs": len(result.get("context", [])),
            "workflow_completed": True
        }
        
    except Exception as e:
        print(f"❌ Multi-agent RAG error: {e}")
        return {
            "success": False,
            "error": str(e),
            "question": question
        }

def test_multi_agent_rag():
    """Test the multi-agent RAG system."""
    print("🧪 Testing Multi-Agent Inspector RAG System\n")
    
    test_questions = [
        "What are the electrical inspection requirements for home inspectors in North Carolina?",
        "What should I inspect in HVAC systems according to InterNACHI standards?",
        "What are the building code requirements for foundation inspections?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_questions)}")
        print(f"{'='*60}")
        
        result = query_inspector_rag(question, thread_id=f"test_{i}")
        
        if result["success"]:
            print(f"✅ Question: {result['question']}")
            print(f"📊 Context documents: {result['context_docs']}")
            print(f"📚 Sources: {len(result['sources'])}")
            
            print(f"\n💭 Response:")
            print(f"{result['response']}")
            
            if result['sources']:
                print(f"\n📚 Sources Used:")
                for j, source in enumerate(result['sources'], 1):
                    print(f"   {j}. {source['source']} (score: {source['score']:.4f})")
        else:
            print(f"❌ Query failed: {result['error']}")
    
    print(f"\n🎉 Multi-Agent RAG testing completed!")

if __name__ == "__main__":
    test_multi_agent_rag()