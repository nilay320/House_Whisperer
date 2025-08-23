from typing import TypedDict, Optional, List, Dict, Tuple
import os, re, yaml
from datetime import datetime
from openai import OpenAI
from langsmith import traceable
import json

# LangGraph
from langgraph.graph import StateGraph, END, START

# Import the base enhanced version
try:
    from .langgraph_report_writer_enhanced import (
        ReportState,
        _get_app_mod,
        node_load_data,
        node_group_by_section,
        _enhance_context_for_search,
        _boost_narrative_scores,
        _query_inspector_rag,
        _generate_custom_narrative,
        _generate_executive_summary,
        _get_severity_badge,
        _get_source_badge,
        node_assemble_enhanced_markdown,
        node_save_draft,
        _load_report_sections,
        _collect_inspection_data,
        get_report_version
    )
except ImportError:
    from langgraph_report_writer_enhanced import (
        ReportState,
        _get_app_mod,
        node_load_data,
        node_group_by_section,
        _enhance_context_for_search,
        _boost_narrative_scores,
        _query_inspector_rag,
        _generate_custom_narrative,
        _generate_executive_summary,
        _get_severity_badge,
        _get_source_badge,
        node_assemble_enhanced_markdown,
        node_save_draft,
        _load_report_sections,
        _collect_inspection_data,
        get_report_version
    )

# Import the fixed render function
try:
    from .langgraph_report_writer_enhanced import _render_enhanced_markdown
except ImportError:
    from langgraph_report_writer_enhanced import _render_enhanced_markdown


def _rerank_with_cohere(narratives: List[Dict], query: str, top_k: int = 5) -> List[Dict]:
    """Use Cohere reranker to improve narrative ordering"""
    try:
        cohere_key = os.getenv('COHERE_API_KEY', '').strip()
        if not cohere_key:
            print("⚠️ Cohere API key not found, using embedding scores only")
            # No Cohere key, return original order
            return narratives[:top_k]
        
        print(f"✅ Cohere reranking enabled (key: ...{cohere_key[-4:]})")
        import cohere
        co = cohere.Client(cohere_key)
        
        # Prepare documents for reranking
        documents = []
        for narrative in narratives:
            text = narrative.get('text', '')
            # Include metadata in the document for better context
            payload = narrative.get('payload', {})
            comment_name = payload.get('comment_name', '')
            full_text = f"{comment_name}. {text}" if comment_name else text
            documents.append(full_text)
        
        if not documents:
            return []
        
        # Rerank using Cohere
        try:
            response = co.rerank(
                model='rerank-english-v3.0',  # Latest model
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                return_documents=False
            )
            
            # Reorder narratives based on rerank results
            reranked = []
            for result in response.results:
                idx = result.index
                original_narrative = narratives[idx].copy()
                # Add rerank score
                original_narrative['rerank_score'] = result.relevance_score
                original_narrative['reranked'] = True
                reranked.append(original_narrative)
            
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] Cohere reranked {len(reranked)} narratives")
            
            return reranked
            
        except Exception as e:
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] Cohere rerank failed: {e}, using original order")
            return narratives[:top_k]
            
    except ImportError:
        if os.getenv("REPORT_LOGS") == "1":
            print("[report] Cohere library not installed, skipping reranking")
        return narratives[:top_k]
    except Exception as e:
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] Reranking error: {e}")
        return narratives[:top_k]


def _retrieve_narratives_enhanced_with_reranker(
    section_key: str, 
    clips: List[Dict], 
    sections_catalog: List[Dict], 
    top_k: int = 10, 
    min_score: float = 0.55
) -> List[Dict]:
    """Enhanced narrative retrieval with Cohere reranking"""
    try:
        qdrant_url = (os.getenv('QDRANT_URL') or '').strip()
        qdrant_key = (os.getenv('QDRANT_API_KEY') or '').strip()
        collection = os.getenv('QDRANT_COLLECTION', 'narratives_v1')
        embedding_model = os.getenv('EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
        
        if not qdrant_url or not qdrant_key:
            return []
        
        # Create enhanced context
        context = _enhance_context_for_search(section_key, clips, sections_catalog)
        if not context:
            return []
        
        # Also prepare simple query for reranking (just the transcripts)
        transcript_query = "\n".join([c.get('transcript', '') for c in clips if c.get('transcript')])
        
        # Create embedding
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        emb = client.embeddings.create(model=embedding_model, input=context)
        vector = emb.data[0].embedding
        
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        qc = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        flt = Filter(must=[FieldCondition(key='section', match=MatchValue(value=section_key))])
        
        # Retrieve MORE candidates for reranking (get 20, rerank will pick best)
        search_res = qc.search(
            collection_name=collection, 
            query_vector=vector, 
            limit=min(20, top_k * 2),  # Get more for reranking
            query_filter=flt
        )
        
        out: List[Dict] = []
        for r in search_res:
            score = float(getattr(r, 'score', 0.0) or 0.0)
            # Lower threshold since reranker will fix ordering
            if score < (min_score * 0.8):  # More lenient
                continue
            payload = getattr(r, 'payload', {}) or {}
            # Compose narrative text
            name = (payload.get('comment_name') or '').strip()
            text = (payload.get('comment_text') or '').strip()
            combined = f"{name}. {text}".strip('. ').strip()
            
            # Determine severity
            comment_type = payload.get('comment_type', 'info')
            severity = 'info'
            if comment_type == 'defect':
                category = payload.get('category', 0)
                if category == 1:
                    severity = 'critical'
                elif category == 0:
                    severity = 'major'
                else:
                    severity = 'minor'
            
            out.append({
                'id': getattr(r, 'id', None),
                'text': combined or text or name,
                'score': score,
                'payload': payload,
                'severity': severity,
                'original_rank': len(out) + 1
            })
        
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] Retrieved {len(out)} candidates for reranking")
        
        # Apply keyword boosting first
        out = _boost_narrative_scores(out, clips)
        
        # Then rerank with Cohere for better semantic matching
        out = _rerank_with_cohere(out, transcript_query, top_k=top_k)
        
        return out
        
    except Exception as e:
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] Enhanced retrieval with reranker error: {e}")
        return []


@traceable(name="retrieve_narratives_with_reranker")
def node_retrieve_narratives_with_reranker(state: ReportState) -> ReportState:
    """Enhanced narrative retrieval with intelligent fallback loop and Cohere reranking"""
    grouped = state.get('grouped', {})
    sections_catalog = state.get('sections_catalog', [])
    narratives_by_section: Dict[str, List[Dict]] = {}
    narrative_sources: Dict[str, str] = {}
    section_severity: Dict[str, str] = {}
    quality_scores: Dict[str, float] = {}
    rag_results: Dict[str, Dict] = {}
    
    for section_key, clips in grouped.items():
        # Step 1: Try enhanced narrative retrieval with reranker
        narratives = _retrieve_narratives_enhanced_with_reranker(
            section_key, clips, sections_catalog
        )
        
        # Check if we have good matches (use rerank score if available)
        if narratives:
            # Use original score for quality tracking, rerank_score is just for ordering
            best_score = narratives[0].get('score', 0)
            rerank_score = narratives[0].get('rerank_score', 0)
            
            # Check if clips mention code-related keywords that should trigger RAG
            code_keywords = ['code', 'violation', 'standard', 'requirement', 'compliance', 'safety']
            transcript_text = ' '.join([c.get('transcript', '') for c in clips]).lower()
            mentions_codes = any(keyword.lower() in transcript_text for keyword in code_keywords)
            
            # Accept narrative if score is good (0.7+ for non-reranked, 0.6+ for reranked)
            high_confidence = best_score >= 0.7 or (narratives[0].get('reranked') and best_score >= 0.6)
            
            if high_confidence and not mentions_codes:
                # High-quality narrative found and no code compliance needed
                narratives_by_section[section_key] = narratives[:3]
                narrative_sources[section_key] = 'reranked_narrative' if narratives[0].get('reranked') else 'verified_narrative'
                # Use the original embedding score for quality, not rerank score
                quality_scores[section_key] = best_score if not narratives[0].get('reranked') else min(best_score * 1.2, 0.95)
                
                # Extract severity from best narrative
                section_severity[section_key] = narratives[0].get('severity', 'info')
                
                if os.getenv("REPORT_LOGS") == "1":
                    if narratives[0].get('reranked'):
                        print(f"[report] {section_key}: 🎯 Reranked narrative (embed={best_score:.2f}, rerank={rerank_score:.2f})")
                    else:
                        print(f"[report] {section_key}: ✅ Verified narrative (score={best_score:.2f})")
            
            else:
                # Low score OR code compliance mentioned - try RAG enhancement
                if os.getenv("REPORT_LOGS") == "1":
                    if mentions_codes:
                        print(f"[report] {section_key}: 📚 Code compliance mentioned, adding RAG...")
                    else:
                        print(f"[report] {section_key}: ⚠️ Low score ({best_score:.2f}), trying RAG...")
                
                # Try RAG to enhance/supplement narratives
                rag_result = _query_inspector_rag(section_key, clips)
                
                if os.getenv("REPORT_LOGS") == "1" and rag_result:
                    print(f"[report] RAG returned with confidence: {rag_result.get('confidence', 0)}")
                
                if rag_result and rag_result.get('confidence', 0) > 0.6:
                    # Combine RAG with existing narratives
                    enhanced_narrative = {
                        'text': rag_result['text'],
                        'score': rag_result['confidence'],
                        'sources': rag_result.get('sources', []),
                        'severity': 'info',
                        'rag_enhanced': True
                    }
                    
                    # RAG first, then best database narratives
                    combined = [enhanced_narrative]
                    combined.extend(narratives[:2])  # Keep top 2 database narratives too
                    
                    narratives_by_section[section_key] = combined
                    # Show it's a hybrid: both RAG and database narratives
                    narrative_sources[section_key] = 'hybrid_code_narrative'
                    quality_scores[section_key] = max(rag_result['confidence'], best_score)  # Use better score
                    rag_results[section_key] = rag_result
                    section_severity[section_key] = narratives[0].get('severity', 'info')  # Keep original severity
                    
                    if os.getenv("REPORT_LOGS") == "1":
                        print(f"[report] {section_key}: 📋 Building code-enhanced + database narratives")
                
                else:
                    # Generate custom narrative
                    if os.getenv("REPORT_LOGS") == "1":
                        print(f"[report] {section_key}: 🤖 Generating custom narrative...")
                    
                    custom_text = _generate_custom_narrative(section_key, clips, sections_catalog)
                    
                    custom_narrative = {
                        'text': custom_text,
                        'score': 0.5,
                        'generated': True,
                        'severity': 'info'
                    }
                    
                    # Combine AI generated with database narratives
                    final_narratives = [custom_narrative]
                    final_narratives.extend(narratives[:2])  # Keep top 2 database narratives
                    
                    narratives_by_section[section_key] = final_narratives
                    narrative_sources[section_key] = 'ai_generated'
                    quality_scores[section_key] = 0.5
                    section_severity[section_key] = 'info'
        else:
            # No narratives found at all - try RAG first, then generate
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] {section_key}: No narratives found, trying Inspector RAG...")
            
            # Try RAG fallback FIRST
            rag_result = _query_inspector_rag(section_key, clips)
            
            if os.getenv("REPORT_LOGS") == "1" and rag_result:
                print(f"[report] RAG returned with confidence: {rag_result.get('confidence', 0)}")
            
            if rag_result and rag_result.get('confidence', 0) > 0.6:
                # Use RAG result
                enhanced_narrative = {
                    'text': rag_result['text'],
                    'score': rag_result['confidence'],
                    'sources': rag_result.get('sources', []),
                    'severity': 'info',
                    'rag_enhanced': True
                }
                
                narratives_by_section[section_key] = [enhanced_narrative]
                narrative_sources[section_key] = 'building_code_enhanced'
                quality_scores[section_key] = rag_result['confidence']
                rag_results[section_key] = rag_result
                section_severity[section_key] = 'info'
                
                if os.getenv("REPORT_LOGS") == "1":
                    print(f"[report] {section_key}: 📋 Building code-enhanced narrative (no DB match)")
            
            else:
                # Generate custom narrative as last resort
                if os.getenv("REPORT_LOGS") == "1":
                    print(f"[report] {section_key}: 🤖 Generating custom narrative...")
                
                custom_text = _generate_custom_narrative(section_key, clips, sections_catalog)
                custom_narrative = {
                    'text': custom_text,
                    'score': 0.5,
                    'generated': True,
                    'severity': 'info'
                }
                
                narratives_by_section[section_key] = [custom_narrative]
                narrative_sources[section_key] = 'ai_generated'
                quality_scores[section_key] = 0.5
                section_severity[section_key] = 'info'
    
    # Update state with all results
    state.update({
        'narratives_by_section': narratives_by_section,
        'narrative_sources': narrative_sources,
        'section_severity': section_severity,
        'quality_scores': quality_scores,
        'rag_results': rag_results
    })
    
    return state


def build_enhanced_report_graph_with_reranker():
    """Build the enhanced report generation graph with Cohere reranking"""
    g = StateGraph(ReportState)
    
    # Add nodes
    g.add_node("load_data", node_load_data)
    g.add_node("group_by_section", node_group_by_section)
    g.add_node("retrieve_narratives_with_reranker", node_retrieve_narratives_with_reranker)
    g.add_node("assemble_enhanced_markdown", node_assemble_enhanced_markdown)
    g.add_node("save_draft", node_save_draft)
    
    # Define edges
    g.add_edge(START, "load_data")
    g.add_edge("load_data", "group_by_section")
    g.add_edge("group_by_section", "retrieve_narratives_with_reranker")
    g.add_edge("retrieve_narratives_with_reranker", "assemble_enhanced_markdown")
    g.add_edge("assemble_enhanced_markdown", "save_draft")
    g.add_edge("save_draft", END)
    
    return g.compile()


@traceable(name="run_enhanced_report_with_reranker")
def run_enhanced_report_with_reranker(inspection_id: str, sections: Optional[List[str]] = None) -> Dict:
    """Run the enhanced report generation with Cohere reranking"""
    graph = build_enhanced_report_graph_with_reranker()
    initial: ReportState = {"inspection_id": inspection_id, "sections_filter": sections or []}
    out: ReportState = graph.invoke(initial)  # type: ignore
    
    return {
        "markdown": out.get("markdown", ""),
        "sectionCount": out.get("section_count", 0),
        "clipCount": out.get("clip_count", 0),
        "saved": out.get("saved", False),
        "executiveSummary": out.get("executive_summary", ""),
        "reportQualityScore": out.get("report_quality_score", 0.5),
        "narrativeSources": out.get("narrative_sources", {}),
        "version": get_report_version()
    }