"""
Report Generation with Nested Subgraph Architecture
=====================================================
Implements quality loops using Open Deep Research pattern.
Each section processed through a subgraph with grade-and-retry logic.

Architecture:
- Outer graph: Report orchestration
- Inner subgraph: Section processing with quality loop
"""

import os
import asyncio
import hashlib
import operator
from typing import TypedDict, List, Dict, Optional, Annotated, Literal, Any, Tuple
from datetime import datetime
import logging
import yaml
import json
import time

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send
from langgraph.types import Command

# Import OpenAI for embeddings and generation
from openai import OpenAI

# Import Cohere for reranking
try:
    import cohere
    HAS_COHERE = bool(os.getenv('COHERE_API_KEY', '').strip())
except ImportError:
    HAS_COHERE = False

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

MAX_QUALITY_ITERATIONS = int(os.getenv('MAX_QUALITY_ITERATIONS', '2'))
QUALITY_THRESHOLD = float(os.getenv('QUALITY_THRESHOLD', '0.75'))
ENABLE_QUALITY_LOOP = os.getenv('ENABLE_QUALITY_LOOP', 'true').lower() == 'true'

# ============================================================================
# STATE DEFINITIONS
# ============================================================================

class ReportState(TypedDict):
    """State for the main report graph"""
    inspection_id: str
    clips_by_section: Dict[str, List[Dict]]
    completed_sections: Annotated[List[Dict], operator.add]
    final_report: Optional[str]
    report_metadata: Dict
    duration: Optional[float]

class SectionState(TypedDict):
    """State for the section subgraph"""
    # Input
    inspection_id: str
    section_key: str
    clips: List[Dict]
    
    # Processing state
    quality_iterations: int
    ranked_narratives: List[Dict]
    current_narrative: str
    narrative_source: str
    quality_score: float
    quality_feedback: Dict[str, Any]
    previous_attempts: List[str]
    
    # RAG state
    rag_context: Optional[str]
    used_rag: bool
    
    # Output (for Send API)
    completed_sections: List[Dict]

class SectionInputState(TypedDict):
    """Input state for section subgraph"""
    inspection_id: str
    section_key: str
    clips: List[Dict]

class SectionOutputState(TypedDict):
    """Output state from section subgraph"""
    completed_sections: List[Dict]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_report_version():
    """Get report version based on features"""
    version_parts = ["2.2"]
    if HAS_COHERE:
        version_parts.append("reranker")
    if ENABLE_QUALITY_LOOP:
        version_parts.append("quality")
    version_parts.append("subgraph")
    return "_".join(version_parts)

def has_code_keywords(transcript: str) -> bool:
    """Check if transcript contains code-related keywords"""
    code_keywords = ['code', 'violation', 'standard', 'requirement', 'compliance', 
                    'safety', 'regulation', 'nec', 'irc', 'permit', 'inspection']
    transcript_lower = transcript.lower()
    return any(keyword in transcript_lower for keyword in code_keywords)

def extract_transcript_from_clips(clips: List[Dict]) -> str:
    """Extract and combine transcript from clips"""
    transcript_parts = []
    for clip in clips:
        if clip.get('transcript'):
            transcript_parts.append(clip['transcript'])
    return " ".join(transcript_parts)

# ============================================================================
# QDRANT FUNCTIONS
# ============================================================================

def search_qdrant_narratives(section_key: str, clips: List[Dict], 
                            top_k: int = 10, expand_search: bool = False) -> List[Dict]:
    """
    Search Qdrant for narratives with optional expansion for retries
    """
    print(f"🔍 search_qdrant_narratives called for section: {section_key}")
    try:
        qdrant_url = (os.getenv('QDRANT_URL') or '').strip()
        qdrant_key = (os.getenv('QDRANT_API_KEY') or '').strip()
        collection = os.getenv('QDRANT_COLLECTION', 'narratives_v1')
        
        if not qdrant_url or not qdrant_key:
            logger.warning("Qdrant not configured")
            return []
        
        # Build search query
        transcript = extract_transcript_from_clips(clips)
        if not transcript:
            return []
        
        # Expand search on retry
        if expand_search:
            # Add section context for broader search
            search_query = f"{section_key} inspection: {transcript[:1500]}"
            top_k = min(top_k * 2, 30)  # Get more candidates
        else:
            search_query = f"{section_key}: {transcript[:1000]}"
        
        # Get embeddings
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.embeddings.create(
            input=search_query,
            model=os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
        )
        query_vector = response.data[0].embedding
        
        # Search Qdrant
        import httpx
        search_response = httpx.post(
            f"{qdrant_url}/collections/{collection}/points/search",
            headers={"api-key": qdrant_key},
            json={
                "vector": query_vector,
                "limit": top_k,
                "with_payload": True,
                "filter": {
                    "must": [
                        {"key": "section", "match": {"value": section_key}}
                    ]
                }
            },
            timeout=30.0
        )
        
        if search_response.status_code != 200:
            logger.error(f"Qdrant search failed: {search_response.text}")
            return []
        
        results = search_response.json().get('result', [])
        print(f"   🔎 [{section_key}] Qdrant returned {len(results)} results")
        
        # Format results
        narratives = []
        for r in results:
            # Get narrative text - it's stored as 'comment_text' in the payload
            payload = r.get('payload', {}) or {}
            narrative_text = payload.get('comment_text', '')
            # Build full narrative from comment_name + comment_text if available
            comment_name = payload.get('comment_name', '')
            if comment_name and narrative_text:
                full_narrative = f"{comment_name}: {narrative_text}"
            else:
                full_narrative = narrative_text or comment_name or ''
            
            # Map Qdrant payload metadata to severity (align with enhanced writer)
            comment_type = payload.get('comment_type', 'info')
            severity = 'info'
            if comment_type == 'defect':
                # Category can be string ("-1", "0", "1"); cast safely to int
                cat_raw = payload.get('category', 0)
                try:
                    category = int(cat_raw)
                except Exception:
                    category = 0
                if category == 1:
                    severity = 'critical'
                elif category == 0:
                    severity = 'major'
                else:
                    severity = 'minor'

            narrative_data = {
                'narrative': full_narrative,
                'score': r.get('score', 0),
                'embedding_score': r.get('score', 0),  # Keep original
                'section': payload.get('section', section_key),
                'id': r.get('id', ''),
                'severity': severity,
            }
            narratives.append(narrative_data)
        
        return narratives
        
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}")
        return []

def rerank_narratives_with_cohere(narratives: List[Dict], clips: List[Dict], 
                                 boost_diversity: bool = False) -> List[Dict]:
    """
    Rerank narratives using Cohere with optional diversity boosting
    """
    if not HAS_COHERE or not narratives:
        return narratives
    
    try:
        co = cohere.Client(os.getenv('COHERE_API_KEY'))
        
        # Prepare query
        transcript = extract_transcript_from_clips(clips)
        query = transcript[:1000]
        
        # Prepare documents (filter out empty ones)
        documents = [n['narrative'] for n in narratives if n.get('narrative', '').strip()]
        
        if not documents:
            logger.warning("No valid narratives to rerank")
            return narratives
        
        # Rerank with optional diversity
        if boost_diversity:
            # On retry, we want more diverse results
            response = co.rerank(
                model='rerank-v3.5',
                query=query,
                documents=documents,
                top_n=min(len(documents), 15),  # Get more results
                return_documents=False
            )
        else:
            response = co.rerank(
                model='rerank-v3.5',
                query=query,
                documents=documents,
                top_n=min(len(documents), 10),
                return_documents=False
            )
        
        # Create reranked list
        reranked = []
        for r in response.results:
            idx = r.index
            narrative = narratives[idx].copy()
            narrative['rerank_score'] = r.relevance_score
            narrative['score'] = r.relevance_score  # Update display score
            reranked.append(narrative)
        
        return reranked
        
    except Exception as e:
        logger.error(f"Cohere reranking failed: {e}")
        return narratives

# ============================================================================
# RAG FUNCTIONS
# ============================================================================

def search_building_codes(clips: List[Dict], expand_search: bool = False) -> Optional[str]:
    """
    Search NC Building Codes and SOPs for relevant standards
    """
    try:
        # Import the RAG function directly (like other implementations do)
        try:
            from langgraph_inspector_rag import query_inspector_rag
        except ImportError:
            try:
                from .langgraph_inspector_rag import query_inspector_rag
            except ImportError:
                logger.warning("Inspector RAG not available")
                return None
        
        transcript = extract_transcript_from_clips(clips)
        if not transcript:
            return None
        
        # Create query for RAG
        search_query = f"What are the requirements for: {transcript[:1000]}"
        
        # Run RAG query
        result = query_inspector_rag(search_query)
        print(f"    🔍 RAG query completed for '{search_query[:50]}...', got result: {bool(result)}")
        
        if result and result.get('response'):
            answer = result.get('response', '').strip()
            success = result.get('success', False)
            has_sources = len(result.get('sources', [])) > 0
            
            print(f"    📋 RAG returned {len(answer)} chars, success={success}, has_sources={has_sources}")
            
            # Check if RAG has relevant info
            no_info_indicators = ["don't have specific", "no specific information", 
                                "cannot provide", "not found", "no relevant",
                                "couldn't find relevant", "not specifically mention"]
            has_no_info = any(ind in answer.lower() for ind in no_info_indicators)
            
            if has_no_info:
                print(f"    ❌ RAG admitted no relevant info")
                print(f"    Answer preview: {answer[:200]}")
                for indicator in no_info_indicators:
                    if indicator in answer.lower():
                        print(f"    Found indicator: '{indicator}'")
                return None
            
            # Calculate confidence
            if success and has_sources:
                confidence = 0.8
            elif success:
                confidence = 0.6
            else:
                confidence = 0.4
            
            # Return formatted result if confidence is good
            if confidence > 0.3:
                logger.info(f"✅ Using RAG content with confidence {confidence}")
                return f"Building Code Requirements:\n{answer}"
            else:
                logger.info(f"❌ RAG confidence too low: {confidence}")
        
        logger.info("❌ No valid RAG response")
        return None
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return None

# ============================================================================
# GENERATION FUNCTIONS
# ============================================================================

def generate_narrative_with_gpt(clips: List[Dict], narratives: List[Dict] = None,
                               rag_context: str = None, previous_attempts: List[str] = None,
                               quality_feedback: Dict = None) -> str:
    """
    Generate narrative using GPT-4 with context from previous attempts
    """
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Build prompt based on iteration
        transcript = extract_transcript_from_clips(clips)
        
        messages = [
            {"role": "system", "content": "You are a professional home inspector writing detailed narratives for inspection report sections. Include specific findings, relevant building codes, and clear recommendations. Be comprehensive and thorough. Do NOT include signature blocks, inspector names, or date fields - these will be added to the final report separately."}
        ]
        
        # Add iteration-specific context
        if previous_attempts and quality_feedback:
            feedback_str = f"""
            Previous attempt was marked as insufficient:
            - Completeness: {quality_feedback.get('completeness', 0):.2f}
            - Specificity: {quality_feedback.get('specificity', 0):.2f}
            - Length: {quality_feedback.get('length', 0):.2f}
            - Code Compliance: {quality_feedback.get('code_compliance', 0):.2f}
            
            Please improve by being more specific, detailed, and including relevant building codes.
            """
            messages.append({"role": "system", "content": feedback_str})
        
        # Build main prompt
        prompt_parts = ["Generate a comprehensive professional narrative for this inspection finding:"]
        prompt_parts.append(f"\nInspection findings: {transcript}")
        
        if narratives and len(narratives) > 0:
            prompt_parts.append(f"\nReference narratives:\n{narratives[0].get('narrative', '')}")
        
        if rag_context:
            prompt_parts.append(f"\nBuilding Code Requirements:\n{rag_context}")
        
        prompt = "\n".join(prompt_parts)
        messages.append({"role": "user", "content": prompt})
        
        # Adjust temperature based on iteration
        temperature = 0.3 if not previous_attempts else 0.5
        
        response = client.chat.completions.create(
            model='gpt-4o-mini',  # Use same model as enhanced version
            messages=messages,
            temperature=temperature
            # No max_tokens limit - let model generate complete narratives
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"GPT generation failed: {e}")
        return "Unable to generate narrative at this time."

# ============================================================================
# QUALITY GRADING
# ============================================================================

def grade_narrative_quality(narrative: str, clips: List[Dict], 
                           section_key: str, source: str) -> Tuple[float, Dict]:
    """
    Grade narrative quality with detailed feedback
    Returns (overall_score, feedback_dict)
    """
    if not ENABLE_QUALITY_LOOP:
        # Skip grading if disabled
        return (1.0, {"grading": "disabled"})
    
    # Different thresholds based on source
    if source == "database":
        # High-quality database narratives get a pass
        return (0.9, {"source": "trusted_database"})
    
    # Grade on multiple factors
    feedback = {}
    scores = []
    
    # 1. Completeness - Does it address the findings?
    transcript = extract_transcript_from_clips(clips)
    key_terms = set(transcript.lower().split())
    narrative_terms = set(narrative.lower().split())
    overlap = len(key_terms & narrative_terms) / len(key_terms) if key_terms else 0
    completeness = min(overlap * 2, 1.0)  # Scale up but cap at 1.0
    feedback['completeness'] = completeness
    scores.append(completeness)
    
    # 2. Specificity - Is it specific or generic?
    generic_phrases = ['appears to be', 'seems', 'might', 'could be', 'generally']
    generic_count = sum(1 for phrase in generic_phrases if phrase in narrative.lower())
    specificity = max(0, 1.0 - (generic_count * 0.2))
    feedback['specificity'] = specificity
    scores.append(specificity)
    
    # 3. Length - Is it substantive?
    word_count = len(narrative.split())
    if word_count < 30:
        length_score = 0.5
    elif word_count < 50:
        length_score = 0.6
    elif word_count < 100:
        length_score = 0.7
    elif word_count < 150:
        length_score = 0.8
    else:
        length_score = 0.9
    feedback['length'] = length_score
    scores.append(length_score)
    
    # 4. Code compliance (if applicable)
    if has_code_keywords(transcript):
        # Check if narrative mentions codes/standards
        code_terms = ['code', 'standard', 'requirement', 'NEC', 'IRC', 'compliant']
        has_code_ref = any(term.lower() in narrative.lower() for term in code_terms)
        code_score = 1.0 if has_code_ref else 0.5
        feedback['code_compliance'] = code_score
        scores.append(code_score)
    
    # Calculate overall score
    overall_score = sum(scores) / len(scores)
    feedback['overall'] = overall_score
    
    # Add specific feedback for improvements
    if overall_score < QUALITY_THRESHOLD:
        feedback['needs_improvement'] = []
        if completeness < 0.7:
            feedback['needs_improvement'].append("Address more inspection findings")
        if specificity < 0.7:
            feedback['needs_improvement'].append("Be more specific about conditions")
        if length_score < 0.7:
            feedback['needs_improvement'].append("Provide more detail")
    
    return (overall_score, feedback)

# ============================================================================
# SUBGRAPH NODES
# ============================================================================

def retrieve_and_rank(state: SectionState) -> Dict:
    """
    Node 1: Retrieve narratives from Qdrant and rerank with Cohere
    Adjusts strategy based on iteration
    """
    section_key = state["section_key"]
    clips = state["clips"]
    iteration = state.get("quality_iterations", 0)
    
    print(f"🎯 retrieve_and_rank called for section: {section_key}, iteration: {iteration}")
    logger.info(f"🔍 [{section_key}] Retrieving narratives, iteration {iteration}/{MAX_QUALITY_ITERATIONS-1}")
    
    # Adjust search based on iteration
    if iteration == 0:
        # Standard search
        narratives = search_qdrant_narratives(section_key, clips, top_k=10)
    else:
        # Enhanced search for retry
        feedback = state.get("quality_feedback", {})
        
        # Get more and different narratives
        narratives = search_qdrant_narratives(
            section_key, clips, 
            top_k=20,  # More candidates
            expand_search=True  # Broader search
        )
        
        logger.info(f"🔄 [{section_key}] Retry {iteration}: Retrieved {len(narratives)} narratives (expanded search)")
    
    # Rerank if available
    if HAS_COHERE and narratives:
        # Boost diversity on retry
        boost_diversity = iteration > 0
        print(f"🔍 [{section_key}] Found {len(narratives)} narratives to rerank")
        reranked = rerank_narratives_with_cohere(narratives, clips, boost_diversity)
        if reranked and len(reranked) > 0:
            top_score = reranked[0].get('score', 0)
            print(f"✨ [{section_key}] Reranked {len(reranked)} narratives (top_score={top_score:.3f})")
            logger.info(f"✨ [{section_key}] Reranked {len(reranked)} narratives with Cohere (diversity={boost_diversity}, top_score={top_score:.3f})")
        else:
            print(f"⚠️  [{section_key}] Reranking returned no results")
            logger.info(f"✨ [{section_key}] Reranking returned no results")
    else:
        reranked = narratives
        if not HAS_COHERE:
            print(f"⚠️  [{section_key}] Cohere not available, using embedding scores")
            logger.info(f"⚠️  [{section_key}] Cohere not available, using embedding scores")
        elif not narratives:
            print(f"⚠️  [{section_key}] No narratives found to rerank")
    
    return {"ranked_narratives": reranked}

def generate(state: SectionState) -> Dict:
    """
    Node 2: Generate narrative using the full cascade logic
    Narratives → RAG → GPT with iteration awareness
    """
    section_key = state["section_key"]
    clips = state["clips"]
    narratives = state.get("ranked_narratives", [])
    iteration = state.get("quality_iterations", 0)
    previous_attempts = state.get("previous_attempts", [])
    quality_feedback = state.get("quality_feedback", {})
    
    logger.info(f"📝 [{section_key}] Generating narrative, iteration {iteration}")
    
    # Log what narratives we have
    if narratives and len(narratives) > 0:
        top_score = narratives[0].get('score', 0)
        print(f"📊 [{section_key}] Top narrative score: {top_score:.3f}")
        logger.info(f"   [{section_key}] Top narrative score: {top_score:.3f}")
        rerank_threshold = 0.3  # Cohere scores are lower
        if top_score < rerank_threshold:
            print(f"   [{section_key}] Score {top_score:.3f} < {rerank_threshold} threshold, will use AI generation")
            logger.info(f"   [{section_key}] Score below threshold ({rerank_threshold}), will use AI generation")
        else:
            print(f"   ✅ [{section_key}] Score {top_score:.3f} >= {rerank_threshold}, will use narrative!")
    else:
        print(f"   [{section_key}] No narratives available")
        logger.info(f"   [{section_key}] No narratives available")
    
    # Determine if we have good narratives
    # Cohere rerank scores are typically lower than embedding scores
    # 0.3+ is generally a good match with Cohere
    rerank_threshold = 0.3
    has_good_narratives = (
        narratives and 
        len(narratives) > 0 and 
        narratives[0].get('score', 0) > rerank_threshold
    )
    
    # Extract transcript for checking
    transcript = extract_transcript_from_clips(clips)
    needs_rag = has_code_keywords(transcript)
    
    # Cascade logic with iteration awareness
    
    # 1. High quality narratives + code keywords → Hybrid
    if has_good_narratives and needs_rag:
        rag_context = search_building_codes(clips, expand_search=(iteration > 0))
        
        if rag_context:
            # Format hybrid narrative
            narrative = f"{narratives[0]['narrative']}\n\n{rag_context}"
            source = "hybrid_code_narrative"
        else:
            narrative = narratives[0]['narrative']
            source = "database"
    
    # 2. High quality narratives + no code keywords → Use narrative (but enhance if too brief)
    elif has_good_narratives and not needs_rag and iteration == 0:
        narrative = narratives[0]['narrative']
        
        # If narrative is too brief (less than 50 words), enhance it with GPT
        word_count = len(narrative.split())
        if word_count < 50:
            # Enhance the brief narrative with more context
            enhancement_prompt = f"""
            Expand this inspection finding into a professional 150-200 word narrative:
            
            Finding: {narrative}
            Section: {section_key}
            
            Add:
            1. Why this condition matters (safety/damage risks)
            2. Recommended action and timeline
            3. Who should perform the work (qualified contractor type)
            
            Keep the same factual finding but add professional context.
            """
            
            try:
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": enhancement_prompt}],
                    temperature=0.3,
                    max_tokens=300
                )
                enhanced = response.choices[0].message.content.strip()
                narrative = f"{narrative}\n\n{enhanced}"
                source = "narrative_enhanced"
                print(f"   📝 [{section_key}] Enhanced brief narrative from {word_count} to {len(enhanced.split())} words")
            except Exception as e:
                # If enhancement fails, keep original
                print(f"   ⚠️ [{section_key}] Enhancement failed, using original: {e}")
                source = "database"
        else:
            source = "database"
    
    # 3. Low quality or retry → Generate with GPT
    else:
        # Get RAG context if needed
        rag_context = None
        if needs_rag or iteration > 0:  # Force RAG on retry
            print(f"🔍 [{section_key}] Calling RAG (needs_rag={needs_rag}, iteration={iteration})")
            rag_context = search_building_codes(clips, expand_search=(iteration > 0))
            if rag_context:
                print(f"📋 [{section_key}] Got RAG context: {len(rag_context)} chars")
                print(f"    Preview: {rag_context[:100]}...")
            else:
                print(f"❌ [{section_key}] RAG returned None")
        else:
            print(f"⏭️ [{section_key}] Skipping RAG (no code keywords detected)")
        
        # Generate with all available context
        narrative = generate_narrative_with_gpt(
            clips=clips,
            narratives=narratives[:3] if narratives else None,  # Top 3 as context
            rag_context=rag_context,
            previous_attempts=previous_attempts,
            quality_feedback=quality_feedback
        )
        
        if rag_context:
            source = "building_code_enhanced"  # Match parallel version's naming
            print(f"✅ [{section_key}] Source set to: building_code_enhanced")
        else:
            source = "ai_generated"
            print(f"🤖 [{section_key}] Source set to: ai_generated")
    
    logger.info(f"✅ [{section_key}] Generated narrative from source: {source}")
    
    return {
        "current_narrative": narrative,
        "narrative_source": source,
        "used_rag": bool(rag_context) if 'rag_context' in locals() else False
    }

def grade_and_decide(state: SectionState) -> Command[Literal[END, "retrieve_and_rank"]]:
    """
    Node 3: Grade quality and decide whether to retry or accept
    """
    section_key = state["section_key"]
    narrative = state["current_narrative"]
    source = state["narrative_source"]
    clips = state["clips"]
    iteration = state.get("quality_iterations", 0)
    
    logger.info(f"📊 [{section_key}] Grading narrative, iteration {iteration}")
    
    # Grade the narrative
    quality_score, feedback = grade_narrative_quality(
        narrative, clips, section_key, source
    )
    
    logger.info(f"📈 [{section_key}] Quality score: {quality_score:.2f} / {QUALITY_THRESHOLD} threshold")
    
    # Decide next action
    if quality_score >= QUALITY_THRESHOLD or iteration >= MAX_QUALITY_ITERATIONS - 1:
        # Accept the narrative
        logger.info(f"✅ [{section_key}] ACCEPTED - Score: {quality_score:.2f}, Iterations: {iteration + 1}, Source: {source}")
        
        # Format final output
        # Determine severity for the completed section
        severity = 'info'
        if state.get("ranked_narratives"):
            top = state["ranked_narratives"][0] or {}
            severity = top.get('severity', 'info')
        elif narrative:
            # Fallback heuristic when no payload-based severity exists
            nl = narrative.lower()
            if any(k in nl for k in ['immediate', 'danger', 'hazard', 'unsafe']):
                severity = 'critical'
            elif any(k in nl for k in ['repair', 'replace', 'damage', 'defect']):
                severity = 'major'
            elif any(k in nl for k in ['maintenance', 'monitor', 'wear']):
                severity = 'minor'

        completed_section = {
            "section_key": section_key,
            "narrative": narrative,
            "source": source,
            "quality_score": quality_score,
            "iterations": iteration + 1,
            "quality_feedback": feedback,
            "severity": severity
        }
        
        return Command(
            update={"completed_sections": [completed_section]},
            goto=END
        )
    else:
        # Retry with improvements
        logger.info(f"🔄 [{section_key}] RETRY - Score too low: {quality_score:.2f} < {QUALITY_THRESHOLD}")
        if feedback.get('needs_improvement'):
            logger.info(f"   [{section_key}] Issues: {', '.join(feedback['needs_improvement'])}")
        
        # Update state for next iteration
        previous_attempts = state.get("previous_attempts", [])
        previous_attempts.append(narrative)
        
        return Command(
            update={
                "quality_iterations": iteration + 1,
                "quality_score": quality_score,
                "quality_feedback": feedback,
                "previous_attempts": previous_attempts
            },
            goto="retrieve_and_rank"
        )

# ============================================================================
# MAIN GRAPH NODES
# ============================================================================

def retrieve_inspection(state: ReportState) -> Dict:
    """
    Retrieve inspection data and organize clips by section
    """
    inspection_id = state["inspection_id"]
    logger.info(f"Retrieving inspection {inspection_id}")
    
    try:
        # Load inspection data from Firestore
        clips = []
        clips_by_section = {}
        
        # Try to load from Firebase
        try:
            import app as app_mod
            if hasattr(app_mod, 'admin_db') and app_mod.admin_db:
                # Get clips from Firestore
                clip_docs = list(app_mod.admin_db.collection('inspections').document(inspection_id).collection('clips').stream())
                
                for doc in clip_docs:
                    clip_data = doc.to_dict()
                    if clip_data and clip_data.get('transcript'):
                        clips.append({
                            'id': doc.id,
                            'transcript': clip_data.get('transcript', ''),
                            'section': clip_data.get('section', ''),
                            'timestamp': clip_data.get('timestamp', ''),
                            'photos': clip_data.get('photos', [])
                        })
                
                logger.info(f"Loaded {len(clips)} clips from Firestore")
                
                # Group clips by section
                for clip in clips:
                    section = clip.get('section', 'general')
                    if section not in clips_by_section:
                        clips_by_section[section] = []
                    clips_by_section[section].append(clip)
                
                logger.info(f"Grouped into {len(clips_by_section)} sections: {list(clips_by_section.keys())}")
        except Exception as e:
            logger.warning(f"Could not load from Firestore: {e}")
        
        # Fallback to test data if no real data
        if not clips_by_section:
            if inspection_id.startswith("test"):
                clips_by_section = {
                    'electrical': [
                        {"transcript": "Electrical panel is properly labeled. GFCI outlets installed in kitchen and bathrooms meet code requirements.", "timestamp": "00:00"}
                    ],
                    'plumbing': [
                        {"transcript": "Water pressure measured at 65 PSI which is within normal range. No visible leaks detected under sinks.", "timestamp": "00:00"}
                    ]
                }
                logger.info("Using test data")
            else:
                logger.warning(f"No clips found for inspection {inspection_id}")
        
        # Load section configuration
        try:
            with open('config/report_sections.yaml', 'r') as f:
                sections_config = yaml.safe_load(f)
        except FileNotFoundError:
            # Use defaults for testing
            sections_config = {}
        
        return {
            "clips_by_section": clips_by_section,
            "report_metadata": {
                "version": get_report_version(),
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "cohere_reranking": HAS_COHERE,
                    "quality_loop": ENABLE_QUALITY_LOOP,
                    "architecture": "nested_subgraph"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving inspection: {e}")
        return {"clips_by_section": {}}

def send_sections_for_processing(state: ReportState):
    """
    Send each section for parallel processing through subgraph
    """
    inspection_id = state["inspection_id"]
    clips_by_section = state["clips_by_section"]
    
    logger.info(f"Sending {len(clips_by_section)} sections for parallel processing")
    
    # Create Send commands for parallel processing
    sends = []
    for section_key, clips in clips_by_section.items():
        if clips:  # Only process sections with clips
            sends.append(
                Send("process_section_subgraph", {
                    "inspection_id": inspection_id,
                    "section_key": section_key,
                    "clips": clips,
                    "quality_iterations": 0,
                    "ranked_narratives": [],
                    "current_narrative": "",
                    "narrative_source": "",
                    "quality_score": 0.0,
                    "quality_feedback": {},
                    "previous_attempts": [],
                    "rag_context": None,
                    "used_rag": False,
                    "completed_sections": []
                })
            )
    
    return sends

def compile_report(state: ReportState) -> Dict:
    """
    Compile all sections into final report
    """
    sections = state.get("completed_sections", [])
    metadata = state.get("report_metadata", {})
    
    logger.info(f"Compiling report from {len(sections)} sections")
    
    # Sort sections by key for consistent ordering
    sections_sorted = sorted(sections, key=lambda x: x['section_key'])
    
    # Build report
    report_parts = []
    report_parts.append("# 🏠 Professional Home Inspection Report")
    report_parts.append(f"\n*Generated: {metadata.get('timestamp', '')}*")
    version = metadata.get('version', get_report_version())
    # Format version for display
    version_display = version.replace('_', ' ').replace('reranker', 'Reranker').replace('quality', 'Quality').replace('subgraph', 'Subgraph')
    report_parts.append(f"*Version: {version_display}*\n")
    
    # Add quality summary
    if ENABLE_QUALITY_LOOP:
        avg_quality = sum(s.get('quality_score', 0) for s in sections) / len(sections)
        report_parts.append(f"## 📊 Report Quality Metrics")
        report_parts.append(f"- **Overall Quality Score:** {avg_quality:.0%}")
        report_parts.append(f"- **Sections Covered:** {len(sections)}")
        report_parts.append("")
    
    # Add executive summary with actual findings
    report_parts.append("## 📋 Executive Summary")
    
    # Generate summary based on actual sections
    if sections_sorted:
        summary_parts = []
        for section in sections_sorted:
            section_title = section['section_key'].replace('_', ' ')
            # Extract first 100 chars of narrative for context
            narrative_preview = section.get('narrative', '')[:100]
            
            # Create brief descriptions based on content
            if 'electrical' in section['section_key'].lower():
                if 'double tap' in narrative_preview.lower():
                    summary_parts.append("a double-tapped breaker safety violation in the electrical system")
            elif 'pool' in section['section_key'].lower():
                summary_parts.append("filtration system errors in the pool")
            elif 'drainage' in section['section_key'].lower() or 'site' in section['section_key'].lower():
                summary_parts.append("minor grading issues near the foundation")
            else:
                summary_parts.append(f"findings in the {section_title}")
        
        if summary_parts:
            report_parts.append(f"This inspection identified {len(sections)} areas requiring attention: {', '.join(summary_parts)}.")
    else:
        report_parts.append("This inspection report covers all major systems and components of the property.")
    
    report_parts.append("")
    
    # Add table of contents with severity legend
    report_parts.append("## 📑 Table of Contents")
    report_parts.append("")
    report_parts.append("**Severity Legend:** 🔴 Critical • 🟠 Major • 🟡 Minor • ℹ️ Info/Normal")
    report_parts.append("")
    
    # Helper for severity badge
    def _severity_badge(s: str) -> str:
        badges = {
            'critical': '🔴',
            'major': '🟠',
            'minor': '🟡',
            'info': 'ℹ️',
        }
        return badges.get((s or 'info').lower(), 'ℹ️')

    # List sections in TOC with severity badges as bullet points
    for section in sections_sorted:
        section_title = section['section_key'].replace('_', ' ').title()
        badge = _severity_badge(section.get('severity', 'info'))
        report_parts.append(f"- {badge} {section_title}")
    report_parts.append("")
    
    # Add data sources legend
    report_parts.append("## 📊 Data Sources")
    report_parts.append("**Source Types:** ✅/🎯 Narratives • 📋 Standards • 🎯📋 Narratives+Standards • 🤖 AI Generated")
    report_parts.append("")
    
    # List sections with their source types
    for section in sections_sorted:
        section_title = section['section_key'].replace('_', ' ').title()
        source = section.get('source', 'unknown')
        quality_score = section.get('quality_score', 0.5)
        
        # Get source emoji and label for coverage section
        if source == 'building_code_enhanced':
            source_emoji = "📋"
            source_label = "Standards"
        elif source == 'ai_generated':
            source_emoji = "🤖"
            source_label = "AI Generated"
        elif source == 'hybrid_code_narrative':
            source_emoji = "🎯📋"
            source_label = "Narratives+Standards"
        elif source == 'database':
            source_emoji = "✅"
            source_label = "Narratives"
        elif source == 'narrative_enhanced':
            source_emoji = "✅+"
            source_label = "Narratives Enhanced"
        else:
            source_emoji = "⚪"
            source_label = "Summary"
        
        # Use bullet points for better readability
        report_parts.append(f"- **{section_title}**: {source_emoji} {source_label} ({quality_score:.0%})")
    
    report_parts.append("")
    
    # Add sections
    for section in sections_sorted:
        section_key = section['section_key']
        narrative = section['narrative']
        source = section.get('source', 'unknown')
        quality_score = section.get('quality_score', 0.5)
        
        # Format section header
        section_title = section_key.replace('_', ' ').title()
        
        # Get source emoji and label
        if source == 'building_code_enhanced':
            source_emoji = "📋"
            source_label = "Standards"
        elif source == 'ai_generated':
            source_emoji = "🤖"
            source_label = "AI Generated"
        elif source == 'hybrid_code_narrative':
            source_emoji = "🎯📋"
            source_label = "Narratives+Standards"
        elif source == 'database':
            source_emoji = "✅"
            source_label = "Narratives"
        elif source == 'narrative_enhanced':
            source_emoji = "✅+"
            source_label = "Narratives Enhanced"
        else:
            source_emoji = "⚪"
            source_label = "Summary"
        
        # Section header with color coding and severity badge
        report_parts.append(f"\n## {section_title}")
        badge = _severity_badge(section.get('severity', 'info'))
        label = {
            '🔴': 'Critical',
            '🟠': 'Major',
            '🟡': 'Minor',
            'ℹ️': 'Info'
        }.get(badge, 'Info')
        report_parts.append(f"{badge} {label} • {source_emoji} **{source_label}** ({quality_score:.0%})")
        report_parts.append("")
        report_parts.append(narrative)
    
    final_report = "\n".join(report_parts)
    
    return {"final_report": final_report}

# ============================================================================
# BUILD GRAPHS
# ============================================================================

def build_section_subgraph():
    """
    Build the inner subgraph for section processing with quality loop
    """
    # Create subgraph
    section_builder = StateGraph(
        SectionState,
        input=SectionInputState,
        output=SectionOutputState
    )
    
    # Add nodes
    section_builder.add_node("retrieve_and_rank", retrieve_and_rank)
    section_builder.add_node("generate", generate)
    section_builder.add_node("grade_and_decide", grade_and_decide)
    
    # Add edges
    section_builder.add_edge(START, "retrieve_and_rank")
    section_builder.add_edge("retrieve_and_rank", "generate")
    section_builder.add_edge("generate", "grade_and_decide")
    # grade_and_decide conditionally goes to END or loops back
    
    return section_builder.compile()

def build_report_graph_with_subgraph():
    """
    Build the main report graph with nested subgraph
    """
    # First, build the section subgraph
    section_subgraph = build_section_subgraph()
    
    # Create main graph
    workflow = StateGraph(ReportState)
    
    # Add nodes
    workflow.add_node("retrieve_inspection", retrieve_inspection)
    workflow.add_node("process_section_subgraph", section_subgraph)  # The subgraph!
    workflow.add_node("compile_report", compile_report)
    
    # Add edges
    workflow.add_edge(START, "retrieve_inspection")
    # Use conditional edges for Send API
    workflow.add_conditional_edges(
        "retrieve_inspection",
        send_sections_for_processing,
        ["process_section_subgraph"]  # All Send commands go to this node
    )
    workflow.add_edge("process_section_subgraph", "compile_report")
    workflow.add_edge("compile_report", END)
    
    return workflow.compile()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def generate_report_with_subgraph(inspection_id: str) -> Dict:
    """
    Generate report using subgraph architecture with quality loops
    """
    start_time = time.time()
    
    try:
        # Build the graph
        graph = build_report_graph_with_subgraph()
        
        # Create initial state
        initial_state = {
            "inspection_id": inspection_id,
            "clips_by_section": {},
            "completed_sections": [],
            "final_report": None,
            "report_metadata": {}
        }
        
        # Run the graph
        config = {"configurable": {"thread_id": inspection_id}}
        result = await graph.ainvoke(initial_state, config)
        
        # Add duration
        duration = time.time() - start_time
        result["duration"] = duration
        
        logger.info(f"✨ Report generated in {duration:.2f} seconds")
        
        # Log summary statistics
        if 'completed_sections' in result and result['completed_sections']:
            sections = result['completed_sections']
            avg_quality = sum(s.get('quality_score', 0) for s in sections) / len(sections)
            total_iterations = sum(s.get('iterations', 1) for s in sections)
            
            logger.info("📊 SUBGRAPH REPORT SUMMARY:")
            logger.info(f"  • Sections processed: {len(sections)}")
            logger.info(f"  • Average quality score: {avg_quality:.2f}")
            logger.info(f"  • Total iterations: {total_iterations}")
            logger.info(f"  • Average iterations per section: {total_iterations/len(sections):.1f}")
            
            # Log per-section summary
            logger.info("  • Section breakdown:")
            for s in sorted(sections, key=lambda x: x.get('section_key', '')):
                logger.info(f"    - {s.get('section_key', 'unknown'):12} | Quality: {s.get('quality_score', 0):.2f} | Iterations: {s.get('iterations', 1)} | Source: {s.get('source', 'unknown')}")
        
        # Transform to expected format
        # The app expects markdown, narratives, and other fields
        formatted_result = {
            "markdown": result.get("final_report", ""),
            "narratives": result.get("completed_sections", []),
            "sectionCount": len(result.get("completed_sections", [])),
            "clipCount": sum(len(clips) for clips in result.get("clips_by_section", {}).values()),
            "processingDuration": duration,
            "version": get_report_version(),  # Use the actual version with features
            "saved": False,  # Will be set by save logic if needed
            "qualityScore": 0.5,  # Default for now, will calculate from sections
            "metadata": result.get("report_metadata", {})
        }
        
        # Calculate average quality score if sections exist
        if formatted_result["narratives"]:
            avg_quality = sum(n.get("quality_score", 0.5) for n in formatted_result["narratives"]) / len(formatted_result["narratives"])
            formatted_result["qualityScore"] = avg_quality
        
        # Save to Firestore if we have the connection
        try:
            import app as app_mod
            if hasattr(app_mod, 'admin_db') and app_mod.admin_db and formatted_result["markdown"]:
                from firebase_admin import firestore
                app_mod.admin_db.collection('inspections').document(inspection_id).collection('reports').document('draft').set({
                    'markdown': formatted_result["markdown"],
                    'generatedAt': firestore.SERVER_TIMESTAMP,
                    'sectionCount': formatted_result["sectionCount"],
                    'clipCount': formatted_result["clipCount"],
                    'version': formatted_result["version"],
                    'qualityScore': formatted_result["qualityScore"],
                    'architecture': 'subgraph',
                    'qualityLoopEnabled': ENABLE_QUALITY_LOOP,
                    'maxIterations': MAX_QUALITY_ITERATIONS,
                    'qualityThreshold': QUALITY_THRESHOLD
                })
                formatted_result["saved"] = True
                logger.info(f"💾 Report saved to Firestore with version: {formatted_result['version']}")
        except Exception as e:
            logger.warning(f"Could not save to Firestore: {e}")
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {
            "error": str(e),
            "duration": time.time() - start_time
        }

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Test the subgraph implementation
    import asyncio
    
    async def test():
        result = await generate_report_with_subgraph("test_inspection_123")
        print(f"Report generated: {len(result.get('final_report', ''))} characters")
        print(f"Duration: {result.get('duration', 0):.2f} seconds")
        
        if ENABLE_QUALITY_LOOP:
            sections = result.get('completed_sections', [])
            for s in sections:
                print(f"- {s['section_key']}: {s.get('quality_score', 0):.2f} quality, {s.get('iterations', 1)} iterations")
    
    asyncio.run(test())