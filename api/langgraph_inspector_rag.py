#!/usr/bin/env python3
"""Multi-Agent LangGraph RAG System for NC Inspector AI following the notebook pattern."""

import os
import json
from typing import Dict, List, Any, TypedDict, Literal
from operator import add

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

# Qdrant client
from qdrant_client import QdrantClient

# Import web search tools
from web_search_tools import search_web_for_inspection_info

# Load environment variables are handled by the FastAPI app on startup

# Configuration
COLLECTION_NAME = 'inspector-standards-postmidterm'
EMBEDDING_MODEL = 'text-embedding-3-small'
CHAT_MODEL = 'gpt-4o-mini'

# Web augmentation configuration (opt-in). If enabled, we do one web search pass
# even when RAG has hits, but only for keyword-triggered queries.
USE_WEB_AUGMENT = os.getenv("USE_WEB_AUGMENT", "0").strip() == "1"
WEB_AUGMENT_KEYWORDS_DEFAULT = (
    "recall,manufacturer,cpsc,best practices,how to,current,update,"
    "installation manual,model,serial,2024"
)
WEB_AUGMENT_KEYWORDS = [
    s.strip().lower() for s in os.getenv("WEB_AUGMENT_KEYWORDS", WEB_AUGMENT_KEYWORDS_DEFAULT).split(",") if s.strip()
]
WEB_TOOL_FETCH_LIMIT = int(os.getenv("WEB_TOOL_FETCH_LIMIT", "8").strip() or 8)
WEB_AUGMENT_MAX = int(os.getenv("WEB_AUGMENT_MAX", "5").strip() or 5)
WEB_MIN_SCORE_GENERIC = float(os.getenv("WEB_MIN_SCORE_GENERIC", "0.4").strip() or 0.4)
WEB_MIN_SCORE_RECALL = float(os.getenv("WEB_MIN_SCORE_RECALL", "0.3").strip() or 0.3)

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
    """Initialize clients with necessary Pydantic rebuilds."""
    global embeddings, llm, qdrant_client
    
    # Validate environment variables
    required_vars = ["OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise ValueError(f"Missing environment variables: {missing}")
    
    if embeddings is None or llm is None:
        # Add back the necessary Pydantic model rebuilding with Callbacks type definition
        try:
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
            
            # Rebuild in correct order
            if hasattr(BaseCache, 'model_rebuild'):
                BaseCache.model_rebuild()
            if hasattr(BaseCallbackManager, 'model_rebuild'):
                BaseCallbackManager.model_rebuild()
            
            # Rebuild the main models now that Callbacks is defined
            OpenAIEmbeddings.model_rebuild()
            ChatOpenAI.model_rebuild()
            
            print("✅ Pydantic models rebuilt with Callbacks defined")
        except Exception as e:
            print(f"⚠️ Model rebuild failed: {e}")
    
    if embeddings is None:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        print("✅ OpenAI Embeddings initialized")
        
    if llm is None:
        llm = ChatOpenAI(
            model=CHAT_MODEL, 
            temperature=0.1,
            request_timeout=30,
            max_retries=2
        )
        print("✅ ChatOpenAI initialized")
        
    if qdrant_client is None:
        qdrant_client = QdrantClient(
            url=os.environ.get("QDRANT_URL"),
            api_key=os.environ.get("QDRANT_API_KEY"),
            timeout=30
        )
        print("✅ Qdrant client initialized")

# Define the state following the notebook pattern
class InspectorRAGState(TypedDict):
    question: str
    context: List[Document]
    web_results: List[Document]  # Added for web search results
    response: str
    inspector_sources: List[Dict[str, Any]]
    messages: List[BaseMessage]
    next_agent: str
    policy_query: str  # latest query proposed by policy
    policy_steps: int  # persisted step counter for loop control

# Initialize vector store connection to Qdrant Cloud
def get_vector_store():
    """Get the Qdrant vector store connection."""
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

@tool
def search_inspector_standards(query: str) -> List[Dict[str, Any]]:
    """
    Optimized search through NC inspector standards, regulations, and building codes.
    Use this for questions about home inspection requirements, standards, or regulations.
    """
    try:
        _initialize_clients()
        
        query_embedding = embeddings.embed_query(query)
        
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=6,
            with_payload=True,
            score_threshold=0.55,  # Relax threshold slightly to improve recall
            search_params={"hnsw_ef": 128, "exact": False}  # Faster approximate search
        )
        
        # Group by source for diversity
        results_by_source = {}
        for hit in search_result:
            payload = hit.payload
            source = payload.get("source", "Unknown")
            
            if source not in results_by_source:
                results_by_source[source] = []
            
            results_by_source[source].append({
                "content": payload.get("content", ""),
                "source": source,
                "category": payload.get("category", "Standards"),
                "score": float(hit.score),
                "type": "regulatory"  # Ready for multi-source
            })
        
        # Take max 3 results per source for diversity
        final_results = []
        for source_results in results_by_source.values():
            final_results.extend(source_results[:3])
        
        return sorted(final_results, key=lambda x: x["score"], reverse=True)[:5]
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

# Agent definitions - can be used for true agentic reasoning
# Removed legacy ReAct agent scaffolding; we use direct tools for speed and predictability

# Removed legacy ReAct agent scaffolding; we use direct tools for speed and predictability

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
            
            # Check if web search would be helpful
            question_lower = state.get("question", "").lower()
            web_triggers = [
                "recall", "manufacturer", "model", "brand",
                "latest", "recent", "2024", "update", "new",
                "best practice", "tips", "how to", "common issues",
                "what do other inspectors", "forum", "discussion"
            ]
            
            should_search_web = any(trigger in question_lower for trigger in web_triggers)
            has_web_results = bool(state.get("web_results"))
            
            # Routing logic
            # Check if we've already done research (not just if key exists, but if it has content)
            has_done_research = bool(state.get("context"))  # True only if context exists AND has items
            # Check if we've attempted research (key exists, even if empty)
            has_attempted_research = "context" in state
            
            # If no research attempted yet, always do research first
            if not has_attempted_research:
                next_agent = "research_agent"
                print("🤖 Supervisor decision: No research attempted yet -> research_agent")
            # After research attempt, check if we should do web search
            # This happens if: no docs found OR query suggests web search would help
            elif (has_attempted_research and should_search_web and not has_web_results):
                next_agent = "web_search_agent"
                print("🤖 Supervisor decision: Need web search -> web_search_agent")
            # If we have attempted research and either have results or web results, synthesize
            elif has_attempted_research and (has_done_research or has_web_results) and (not state.get("response") or len(state.get("response", "").strip()) == 0):
                next_agent = "synthesis_agent"
                print("🤖 Supervisor decision: Have results, no response -> synthesis_agent")
            # Special case: if research found nothing AND web search isn't triggered by keywords, still do web search
            elif has_attempted_research and not has_done_research and not has_web_results and not should_search_web:
                next_agent = "web_search_agent"
                print("🤖 Supervisor decision: No results from research, trying web search -> web_search_agent")
            # If we have a response, we're done
            elif state.get("response") and len(state.get("response", "").strip()) > 0:
                next_agent = "FINISH"
                print("🤖 Supervisor decision: Have response -> FINISH")
            else:
                # Fallback: if nothing else matches, finish
                next_agent = "FINISH"
                print("🤖 Supervisor decision: Fallback -> FINISH")
        
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

def policy_node(state: InspectorRAGState) -> InspectorRAGState:
    """LLM policy that decides next action: 'rag', 'web', or 'finalize'."""
    try:
        question = state.get("question", "")
        last_summary = ""
        if state.get("context"):
            # brief summary signal for planning
            first = state["context"][0].metadata if state["context"] else {}
            last_summary = f"ctx:{first.get('source','')} n={len(state['context'])}"
        if state.get("web_results"):
            last_summary += f" web={len(state['web_results'])}"

        plan_prompt = (
            "Decide the next action to answer an NC home inspection standards question.\n"
            "Prefer 'rag' search first (InterNACHI, NCHILB, NC codes). Use 'web' only if RAG seems insufficient.\n"
            "Respond JSON: {\"action\": 'rag'|'web'|'finalize', \"query\": <string>}\n"
            f"Question: {question}\n"
            f"Signal: {last_summary}\n"
        )
        plan_msg = llm.invoke([HumanMessage(content=plan_prompt)])
        import json as _json
        text = getattr(plan_msg, 'content', str(plan_msg)) or "{}"
        try:
            parsed = _json.loads(text)
        except Exception:
            parsed = {"action": "rag", "query": question}

        action = (parsed.get("action") or "rag").lower()
        query = parsed.get("query") or question
        return {**state, "next_agent": action, "policy_query": query}
    except Exception as e:
        print(f"policy_node error: {e}")
        return {**state, "next_agent": "rag", "policy_query": state.get("question", "")}


def rag_tool_node(state: InspectorRAGState) -> InspectorRAGState:
    """Execute RAG search and append to context and sources."""
    try:
        query = state.get("policy_query") or state.get("question", "")
        hits = search_inspector_standards.invoke({"query": query})
        ctx = state.get("context", [])
        srcs = state.get("inspector_sources", [])
        steps = int(state.get("policy_steps", 0)) + 1
        for item in hits or []:
            if "error" in item:
                continue
            doc = Document(
                page_content=item.get("content", ""),
                metadata={
                    "source": item.get("source", "Unknown"),
                    "category": item.get("category", "Standards"),
                    "score": float(item.get("score", 0.0)),
                    "type": item.get("type", "regulatory")
                }
            )
            ctx.append(doc)
            srcs.append({
                "source": item.get("source", "Unknown"),
                "score": float(item.get("score", 0.0)),
                "type": item.get("type", "regulatory")
            })
        return {**state, "context": ctx, "inspector_sources": srcs, "policy_steps": steps}
    except Exception as e:
        print(f"rag_tool_node error: {e}")
        return state


def web_tool_node(state: InspectorRAGState) -> InspectorRAGState:
    """Execute web search and append to web_results and sources."""
    try:
        query = state.get("policy_query") or state.get("question", "")
        # Choose a min_score based on recall/manufacturer intent
        ql = (query or "").lower()
        is_recallish = any(k in ql for k in ["recall", "cpsc", "manufacturer", "model", "serial"])
        min_score = WEB_MIN_SCORE_RECALL if is_recallish else WEB_MIN_SCORE_GENERIC
        results = search_web_for_inspection_info.invoke({
            "query": query,
            "max_results": WEB_TOOL_FETCH_LIMIT,
            "min_score": min_score
        })
        web_docs = state.get("web_results", [])
        srcs = state.get("inspector_sources", [])
        steps = int(state.get("policy_steps", 0)) + 1
        # Only keep top WEB_AUGMENT_MAX for synthesis clarity
        for res in (results or [])[:WEB_AUGMENT_MAX]:
            if "error" in res:
                continue
            doc = Document(
                page_content=res.get("content", ""),
                metadata={
                    "source": res.get("source", "Unknown"),
                    "url": res.get("url", ""),
                    "score": float(res.get("score", 0.0)),
                    "type": res.get("type", "web_resource")
                }
            )
            web_docs.append(doc)
            srcs.append({
                "source": res.get("source", "Unknown"),
                "url": res.get("url", ""),
                "type": res.get("type", "web_resource"),
                "score": float(res.get("score", 0.0))
            })
        return {**state, "web_results": web_docs, "inspector_sources": srcs, "policy_steps": steps}
    except Exception as e:
        print(f"web_tool_node error: {e}")
        return state

def web_search_node(state: InspectorRAGState) -> InspectorRAGState:
    """Web search agent node using direct calls (fast path)."""
    import time
    search_start = time.time()
    
    try:
        print(f"🌐 Web search starting for: {state['question']}")
        
        # Ensure clients are initialized
        _initialize_clients()
        
        # Direct web search - faster and more predictable
        web_results = search_web_for_inspection_info.invoke({"query": state["question"]})
        
        # Convert to Documents for consistency
        web_docs = []
        for result in web_results:
            if "error" not in result:
                doc = Document(
                    page_content=result["content"],
                    metadata={
                        "source": result["source"],
                        "url": result.get("url", ""),
                        "score": result.get("score", 0.0),
                        "type": result.get("type", "web_resource")
                    }
                )
                web_docs.append(doc)
        
        search_time = time.time() - search_start
        print(f"🌐 Web search complete: Found {len(web_docs)} relevant resources in {search_time:.2f}s")
        
        # Extract sources for display
        web_sources = []
        for doc in web_docs:
            web_sources.append({
                "source": doc.metadata.get("source", "Unknown"),
                "url": doc.metadata.get("url", ""),
                "type": doc.metadata.get("type", "web_resource"),
                "score": doc.metadata.get("score", 0.0)
            })
        
        return {
            **state,
            "web_results": web_docs,
            "inspector_sources": state.get("inspector_sources", []) + web_sources,
            "next_agent": "synthesis_agent"  # After web search, go to synthesis
        }
        
    except Exception as e:
        print(f"Web search error: {e}")
        return {
            **state,
            "web_results": [],
            "next_agent": "synthesis_agent"  # Continue even if web search fails
        }

def synthesis_node(state: InspectorRAGState) -> InspectorRAGState:
    """Synthesis agent node - optimized for speed."""
    import time
    synthesis_start = time.time()
    
    try:
        print(f"✍️ Fast synthesis starting...")
        
        # Ensure clients are initialized
        _initialize_clients()
        
        # Group context by source type
        regulatory_docs = state.get("context", [])
        web_docs = state.get("web_results", [])
        
        print(f"✍️ Synthesis state - regulatory_docs: {len(regulatory_docs)}, web_docs: {len(web_docs)}")
        
        # Build structured context
        context_parts = []
        
        if regulatory_docs:
            reg_content = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}"
                for doc in regulatory_docs[:6]
            ])
            context_parts.append(f"REGULATORY SOURCES:\n{reg_content}")
        
        if web_docs:  # Web search results
            # Debug: print first doc content preview
            if web_docs:
                print(f"✍️ First web doc preview: {web_docs[0].page_content[:200]}...")
            
            web_content = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\nURL: {doc.metadata.get('url', '')}\n{doc.page_content}"
                for doc in web_docs[:3]
            ])
            context_parts.append(f"WEB RESOURCES:\n{web_content}")
        
        context_text = "\n\n".join(context_parts) if context_parts else "No relevant context found."
        
        print(f"✍️ Context text length: {len(context_text)}, Parts: {len(context_parts)}")
        
        synthesis_prompt = f"""You are a North Carolina home inspection expert. Answer the question using ONLY the provided research context.

        QUESTION: {state['question']}

        RESEARCH CONTEXT:
        {context_text}

        INSTRUCTIONS:
        - Answer based on the provided context above
        - When REGULATORY SOURCES are present, prioritize them for requirements and standards
        - When WEB RESOURCES are present, use them for best practices, current information, and practical tips
        - Clearly distinguish between mandatory requirements (from regulations) and recommended practices (from web sources)
        - If the sources provide relevant information, summarize what you found even if it doesn't completely answer the question
        - If no relevant information is found, say "I couldn't find relevant information in the available sources"
        - Include specific details, standards, and procedures from the sources
        - Do NOT include a separate "Sources" or "References" section; the application will display sources from the trace. You may mention source names inline if helpful, but do not list URLs.
        - When presenting information from web sources, include key details and findings
        - Format professionally for working home inspectors
        - Keep response focused and relevant to the question"""

#on 2
#     # - If the context doesn't contain enough information to answer the question, say "I don't have enough information in the provided sources to answer this question"

#         synthesis_prompt = f"""You are a North Carolina home inspection expert. Based on the following research about "{state['question']}":

# {context_text}

# Create a comprehensive, well-organized response that addresses the question thoroughly. 
# Include specific requirements, standards, and procedures where applicable. 
# Format your response professionally for working home inspectors.
# Can you cite the sources you used at the end?"""

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

def should_continue(state: InspectorRAGState) -> Literal["research_agent", "web_search_agent", "synthesis_agent", "__end__"]:
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
    elif next_agent == "web_search_agent":
        print("🌐 Continuing to web_search_agent")
        return "web_search_agent"
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
    """Create the agentic LangGraph workflow with a policy+tools loop."""
    workflow = StateGraph(InspectorRAGState)

    # Nodes
    workflow.add_node("policy", policy_node)
    workflow.add_node("rag_tool", rag_tool_node)
    workflow.add_node("web_tool", web_tool_node)
    workflow.add_node("synthesis", synthesis_node)

    # Start at policy
    workflow.add_edge(START, "policy")
    # Always go RAG first with the policy's query
    workflow.add_edge("policy", "rag_tool")

    # After RAG: if any context, synthesize; else try web once.
    # If augmentation is enabled and the query matches keywords, do one web pass even with context.
    def after_rag(state: InspectorRAGState):
        ctx_len = len(state.get("context", []) or [])
        if ctx_len == 0:
            return "web_tool"
        if USE_WEB_AUGMENT:
            q = (state.get("policy_query") or state.get("question", "")).lower()
            if any(k in q for k in WEB_AUGMENT_KEYWORDS):
                return "web_tool"
        return "synthesis"

    workflow.add_conditional_edges("rag_tool", after_rag, {
        "synthesis": "synthesis",
        "web_tool": "web_tool",
    })

    # After web: always synthesize
    workflow.add_edge("web_tool", "synthesis")

    # End after synthesis
    workflow.add_edge("synthesis", END)

    memory = MemorySaver()
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
        
        # Initial state - don't include context/web_results keys until agents populate them
        initial_state = {
            "question": question,
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
                
                elif node_name == "web_search_agent":
                    if "web_results" in state and len(state.get("web_results", [])) > 0:
                        web_count = len(state["web_results"])
                        yield {"type": "progress", "message": f"Found {web_count} web resources... ({node_elapsed:.1f}s)"}
                    else:
                        yield {"type": "progress", "message": "Searching the web for current information..."}
                
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
    
    # Initial state - don't include context/web_results keys until agents populate them
    initial_state = {
        "question": question,
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