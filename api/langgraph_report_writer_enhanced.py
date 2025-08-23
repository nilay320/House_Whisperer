from typing import TypedDict, Optional, List, Dict, Tuple
import os, re, yaml
from datetime import datetime
from openai import OpenAI
from langsmith import traceable
import json

# LangGraph
from langgraph.graph import StateGraph, END, START

_APP_MOD = None

def _get_app_mod():
    global _APP_MOD
    if _APP_MOD is not None:
        return _APP_MOD
    # Try imports lazily to avoid circular import at module load time
    for path in (".app", "api.app", "app"):
        try:
            if path == ".app":
                from . import app as m  # type: ignore
            elif path == "api.app":
                import api.app as m  # type: ignore
            else:
                import app as m  # type: ignore
            _APP_MOD = m
            return m
        except Exception:
            continue
    raise RuntimeError("Could not import app module for report writer")


class ReportState(TypedDict, total=False):
    inspection_id: str
    sections_filter: Optional[List[str]]
    # Loaded data
    clips: List[Dict]
    inspection_meta: Dict
    sections_catalog: List[Dict]
    narratives_by_section: Dict[str, List[Dict]]
    # Enhanced tracking
    narrative_sources: Dict[str, str]  # Track source type per section
    section_severity: Dict[str, str]   # Track severity per section
    quality_scores: Dict[str, float]   # Track quality per section
    rag_results: Dict[str, Dict]       # Store RAG results if used
    # Grouped
    grouped: Dict[str, List[Dict]]
    # Output
    markdown: str
    section_count: int
    clip_count: int
    saved: bool
    section_metadata: Dict[str, Dict]
    executive_summary: str
    report_quality_score: float


@traceable(name="load_data")
def node_load_data(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    clips, _, inspection_meta = _collect_inspection_data(inspection_id)
    sections_catalog = _load_report_sections()
    narratives_by_section = {}
    narrative_sources = {}
    section_severity = {}
    quality_scores = {}
    rag_results = {}
    
    state.update({
        "clips": clips,
        "inspection_meta": inspection_meta,
        "sections_catalog": sections_catalog,
        "narratives_by_section": narratives_by_section,
        "narrative_sources": narrative_sources,
        "section_severity": section_severity,
        "quality_scores": quality_scores,
        "rag_results": rag_results,
    })
    if os.getenv("REPORT_LOGS") == "1":
        print(f"[report] load_data: inspection={inspection_id} clips={len(clips)} sections={len(sections_catalog)}")
    return state


@traceable(name="group_by_section")
def node_group_by_section(state: ReportState) -> ReportState:
    clips = state.get("clips", [])
    allowed = set(state.get("sections_filter") or [])
    grouped: Dict[str, List[Dict]] = {}
    for c in clips:
        key = (c.get("section") or "general").strip()
        if allowed and key not in allowed:
            continue
        grouped.setdefault(key, []).append(c)
    if not grouped:
        grouped = {}
    state["grouped"] = grouped
    if os.getenv("REPORT_LOGS") == "1":
        print(f"[report] group_by_section: groups={list(grouped.keys())}")
    return state


def _enhance_context_for_search(section_key: str, clips: List[Dict], sections_catalog: List[Dict]) -> str:
    """Create enhanced context for better narrative matching"""
    # Get section label for better context
    section_label = section_key
    for s in sections_catalog:
        if s.get('key') == section_key:
            section_label = s.get('label', section_key)
            break
    
    # Combine transcripts with section context
    transcripts = []
    for c in clips:
        if c.get('transcript'):
            transcripts.append(c.get('transcript'))
    
    # Enhanced context includes section name and all transcripts
    context_parts = [
        f"Section: {section_label}",
        f"Section Key: {section_key}",
        "Inspection findings:",
        "\n".join(transcripts)
    ]
    
    return "\n".join(context_parts).strip()


def _boost_narrative_scores(narratives: List[Dict], clips: List[Dict]) -> List[Dict]:
    """Boost scores for narratives with keyword matches"""
    # Extract key terms from transcripts
    all_text = " ".join([c.get('transcript', '') for c in clips]).lower()
    
    # Common inspection keywords to check
    boost_keywords = [
        'leak', 'damage', 'crack', 'missing', 'broken', 'disconnect',
        'improper', 'safety', 'hazard', 'defect', 'deteriorat', 'corrosion',
        'moisture', 'stain', 'rot', 'rust', 'worn', 'fail'
    ]
    
    # Check which keywords appear in transcripts
    present_keywords = [kw for kw in boost_keywords if kw in all_text]
    
    # Boost narratives that contain matching keywords
    for narrative in narratives:
        narrative_text = narrative.get('text', '').lower()
        boost = 0.0
        
        for keyword in present_keywords:
            if keyword in narrative_text:
                boost += 0.05  # Boost by 5% per matching keyword
        
        # Apply boost but cap at 0.99
        original_score = narrative.get('score', 0.0)
        narrative['score'] = min(0.99, original_score + boost)
        narrative['boosted'] = boost > 0
    
    # Re-sort by new scores
    narratives.sort(key=lambda x: x.get('score', 0), reverse=True)
    return narratives


def _retrieve_narratives_enhanced(section_key: str, clips: List[Dict], sections_catalog: List[Dict], top_k: int = 10, min_score: float = 0.55) -> List[Dict]:
    """Enhanced narrative retrieval with better context and scoring"""
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
        
        # Create embedding
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        emb = client.embeddings.create(model=embedding_model, input=context)
        vector = emb.data[0].embedding
        
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        qc = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        flt = Filter(must=[FieldCondition(key='section', match=MatchValue(value=section_key))])
        
        # Retrieve more candidates for better selection
        search_res = qc.search(collection_name=collection, query_vector=vector, limit=top_k, query_filter=flt)
        
        out: List[Dict] = []
        for r in search_res:
            score = float(getattr(r, 'score', 0.0) or 0.0)
            if score < min_score:
                continue
            payload = getattr(r, 'payload', {}) or {}
            # Compose narrative text
            name = (payload.get('comment_name') or '').strip()
            text = (payload.get('comment_text') or '').strip()
            combined = f"{name}. {text}".strip('. ').strip()
            
            # Determine severity from comment type
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
            })
        
        # Apply keyword boosting
        out = _boost_narrative_scores(out, clips)
        
        return out
    except Exception as e:
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] narrative retrieval error: {e}")
        return []


def _query_inspector_rag(section_key: str, clips: List[Dict]) -> Optional[Dict]:
    """Query the Inspector RAG system for building codes and standards"""
    try:
        # Try to import the inspector RAG module
        try:
            from .langgraph_inspector_rag import query_inspector_rag
        except ImportError:
            try:
                from api.langgraph_inspector_rag import query_inspector_rag
            except ImportError:
                try:
                    from langgraph_inspector_rag import query_inspector_rag
                except ImportError:
                    # RAG not available, return None
                    if os.getenv("REPORT_LOGS") == "1":
                        print(f"[report] Inspector RAG not available, skipping")
                    return None
        
        # Prepare context from clips
        context_parts = []
        for clip in clips:
            if clip.get('transcript'):
                context_parts.append(clip['transcript'])
        
        if not context_parts:
            return None
        
        # Create query for RAG
        query = f"What are the building code requirements and safety standards for: {' '.join(context_parts[:3])}"
        
        # Run RAG query
        result = query_inspector_rag(query)
        
        if result and result.get('response'):
            response_text = result['response'].lower()
            # Check if RAG admits it doesn't have relevant info
            no_info_phrases = ["couldn't find relevant", "no relevant information", 
                              "not specifically mention", "does not specifically address"]
            admits_no_info = any(phrase in response_text for phrase in no_info_phrases)
            
            # Calculate confidence based on success and sources
            has_sources = len(result.get('sources', [])) > 0
            success = result.get('success', False)
            
            # Lower confidence if RAG admits it doesn't have info
            if admits_no_info:
                confidence = 0.4  # Below threshold
            elif success and has_sources:
                confidence = 0.8
            elif success:
                confidence = 0.65
            else:
                confidence = 0.5
            
            return {
                'text': result['response'],
                'sources': result.get('sources', []),
                'confidence': confidence
            }
        
        return None
        
    except Exception as e:
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] RAG query error: {e}")
        return None


def _generate_custom_narrative(section_key: str, clips: List[Dict], sections_catalog: List[Dict]) -> str:
    """Generate custom narrative using GPT-4 when no good matches found"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Get section label
        section_label = section_key
        for s in sections_catalog:
            if s.get('key') == section_key:
                section_label = s.get('label', section_key)
                break
        
        # Prepare context
        transcripts = []
        for clip in clips[:5]:  # Limit to avoid token overflow
            if clip.get('transcript'):
                transcripts.append(f"- {clip['transcript']}")
        
        context = "\n".join(transcripts)
        
        prompt = f"""You are a professional home inspector writing a narrative for a report section.
Section: {section_label}

Inspector's observations:
{context}

Write a professional, objective narrative (2-3 sentences) that:
1. Describes the condition or issue found
2. Explains why it matters or potential implications
3. Recommends appropriate action if needed

Use standard inspection terminology. Be factual, not alarmist.
IMPORTANT: Do NOT use tables or pipe characters (|). Use only plain text."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a professional home inspector."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        if os.getenv("REPORT_LOGS") == "1":
            print(f"[report] Custom narrative generation error: {e}")
        return "Inspection findings documented. Further evaluation recommended."


@traceable(name="retrieve_narratives_with_fallback")
def node_retrieve_narratives_with_fallback(state: ReportState) -> ReportState:
    """Enhanced narrative retrieval with intelligent fallback loop"""
    grouped = state.get('grouped', {})
    sections_catalog = state.get('sections_catalog', [])
    narratives_by_section: Dict[str, List[Dict]] = {}
    narrative_sources: Dict[str, str] = {}
    section_severity: Dict[str, str] = {}
    quality_scores: Dict[str, float] = {}
    rag_results: Dict[str, Dict] = {}
    
    for section_key, clips in grouped.items():
        # Step 1: Try enhanced narrative retrieval
        narratives = _retrieve_narratives_enhanced(section_key, clips, sections_catalog)
        
        if narratives and narratives[0]['score'] >= 0.7:
            # High-quality narrative found
            narratives_by_section[section_key] = narratives[:3]  # Top 3
            narrative_sources[section_key] = 'verified_narrative'
            quality_scores[section_key] = narratives[0]['score']
            
            # Extract severity from best narrative
            section_severity[section_key] = narratives[0].get('severity', 'info')
            
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] {section_key}: ✅ Verified narrative (score={narratives[0]['score']:.2f})")
        
        else:
            # Low-quality match - enter fallback loop
            if os.getenv("REPORT_LOGS") == "1":
                best_score = narratives[0]['score'] if narratives else 0
                print(f"[report] {section_key}: ⚠️ Low narrative score ({best_score:.2f}), trying fallback...")
            
            # Step 2: Try Inspector RAG
            rag_result = _query_inspector_rag(section_key, clips)
            
            if rag_result and rag_result.get('confidence', 0) > 0.6:
                # Good RAG result - use it
                enhanced_narrative = {
                    'text': rag_result['text'],
                    'score': rag_result['confidence'],
                    'sources': rag_result.get('sources', []),
                    'severity': 'info',
                    'rag_enhanced': True
                }
                
                # Combine with any partial narratives
                combined = [enhanced_narrative]
                if narratives:
                    combined.extend(narratives[:2])  # Add best original narratives
                
                narratives_by_section[section_key] = combined
                narrative_sources[section_key] = 'building_code_enhanced'
                quality_scores[section_key] = rag_result['confidence']
                rag_results[section_key] = rag_result
                section_severity[section_key] = 'info'
                
                if os.getenv("REPORT_LOGS") == "1":
                    print(f"[report] {section_key}: 📋 Building code-enhanced narrative")
            
            else:
                # Step 3: Generate custom narrative as last resort
                if os.getenv("REPORT_LOGS") == "1":
                    print(f"[report] {section_key}: 🤖 Generating custom narrative...")
                
                custom_text = _generate_custom_narrative(section_key, clips, sections_catalog)
                
                custom_narrative = {
                    'text': custom_text,
                    'score': 0.5,
                    'generated': True,
                    'severity': 'info'
                }
                
                # Include any partial matches
                final_narratives = [custom_narrative]
                if narratives:
                    final_narratives.extend(narratives[:2])
                
                narratives_by_section[section_key] = final_narratives
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


def _generate_executive_summary(grouped: Dict[str, List[Dict]], section_metadata: Dict[str, Dict], inspection_meta: Dict) -> str:
    """Generate executive summary for the report"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Count findings by severity
        severity_counts = {'critical': 0, 'major': 0, 'minor': 0, 'info': 0}
        for meta in section_metadata.values():
            severity = meta.get('severity', 'info')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Prepare context
        address = inspection_meta.get('address', 'Property')
        total_sections = len(grouped)
        total_clips = sum(len(clips) for clips in grouped.values())
        
        context = f"""Property: {address}
Sections inspected: {total_sections}
Total observations: {total_clips}
Critical issues: {severity_counts['critical']}
Major issues: {severity_counts['major']}
Minor issues: {severity_counts['minor']}
Informational items: {severity_counts['info']}

Generate a professional 2-3 paragraph executive summary that:
1. Provides overall assessment of the property
2. Highlights any critical or major findings
3. Gives a balanced perspective without being alarmist

IMPORTANT: Use ONLY paragraphs and bullet points. Do NOT use tables or pipe characters (|)."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            messages=[
                {"role": "system", "content": "You are a professional home inspector writing an executive summary."},
                {"role": "user", "content": context}
            ]
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception:
        # Fallback summary
        return f"This inspection report covers {len(grouped)} sections of the property with {sum(len(clips) for clips in grouped.values())} total observations documented."


def _get_severity_badge(severity: str) -> str:
    """Get visual badge for severity level"""
    badges = {
        'critical': '🔴 **Critical**',
        'major': '🟠 **Major**',
        'minor': '🟡 **Minor**',
        'info': 'ℹ️ **Info**'
    }
    return badges.get(severity, 'ℹ️ **Info**')


def _get_source_badge(source: str, score: float = 0) -> str:
    """Get visual badge for narrative source"""
    if source == 'verified_narrative':
        return f'✅ **Verified Narratives** ({score:.0%} match)'
    elif source == 'reranked_narrative':
        return f'🎯 **Reranked Narratives** ({score:.0%} match)'
    elif source == 'hybrid_code_narrative':
        return f'🎯📋 **Narratives + Standards** ({score:.0%} confidence)'
    elif source == 'building_code_enhanced':
        return f'📋 **Standards-Based** ({score:.0%} confidence)'
    elif source == 'ai_generated':
        return '🤖 **AI Generated**'
    else:
        return '⚪ **Summary**'


@traceable(name="assemble_enhanced_markdown")
def node_assemble_enhanced_markdown(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    grouped = state.get("grouped", {})
    sections_catalog = state.get("sections_catalog", [])
    narratives_by_section = state.get("narratives_by_section", {})
    narrative_sources = state.get("narrative_sources", {})
    section_severity = state.get("section_severity", {})
    quality_scores = state.get("quality_scores", {})
    inspection_meta = state.get("inspection_meta", {})
    
    markdown, section_count, clip_count, section_metadata, executive_summary, report_quality = _render_enhanced_markdown(
        inspection_id, grouped, sections_catalog, narratives_by_section, 
        narrative_sources, section_severity, quality_scores, inspection_meta
    )
    
    state.update({
        "markdown": markdown,
        "section_count": section_count,
        "clip_count": clip_count,
        "section_metadata": section_metadata,
        "executive_summary": executive_summary,
        "report_quality_score": report_quality
    })
    return state


def _render_enhanced_markdown(
    inspection_id: str, 
    grouped: Dict[str, List[Dict]], 
    sections_catalog: List[Dict], 
    narratives_by_section: Dict,
    narrative_sources: Dict,
    section_severity: Dict,
    quality_scores: Dict,
    inspection_meta: Dict = None
) -> Tuple[str, int, int, Dict[str, Dict], str, float]:
    """Render enhanced markdown with professional formatting"""
    
    def _label_for(key: str) -> str:
        for s in sections_catalog:
            if s.get('key') == key:
                return s.get('label') or key
        return key
    
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    section_count = len(grouped)
    clip_count = sum(len(v) for v in grouped.values())
    lines: List[str] = []
    section_meta: Dict[str, Dict] = {}
    
    # Calculate report quality score
    avg_quality = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0.5
    # Count both verified and reranked narratives as "verified" (they're from the database)
    verified_count = sum(1 for src in narrative_sources.values() if src in ['verified_narrative', 'reranked_narrative'])
    quality_bonus = (verified_count / len(narrative_sources)) * 0.3 if narrative_sources else 0
    report_quality = min(1.0, avg_quality + quality_bonus)
    
    # Professional Header
    inspection_meta = inspection_meta or {}
    address = inspection_meta.get('address', '').strip()
    
    lines.append("# 🏠 Professional Home Inspection Report")
    lines.append("")
    
    if address:
        lines.append(f"**Property Address:** {address}")
    lines.append(f"**Inspection Date:** {now}")
    lines.append(f"**Report ID:** {inspection_id}")
    lines.append("")
    
    # Report Quality Indicator
    lines.append("## 📊 Report Quality Metrics")
    lines.append(f"- **Overall Quality Score:** {report_quality:.0%}")
    lines.append(f"- **Sections Covered:** {section_count}")
    lines.append(f"- **Total Observations:** {clip_count}")
    lines.append(f"- **Verified Narratives:** {verified_count}/{len(narrative_sources)}")
    lines.append("")
    
    # Generate Executive Summary
    executive_summary = _generate_executive_summary(grouped, section_severity, inspection_meta)
    lines.append("## 📋 Executive Summary")
    lines.append(executive_summary)
    lines.append("")
    
    # Table of Contents with Severity Legend
    lines.append("## 📑 Table of Contents")
    lines.append("")
    lines.append("**Severity Legend:** 🔴 Critical • 🟠 Major • 🟡 Minor • ℹ️ Info/Normal")
    lines.append("")
    for i, key in enumerate(grouped.keys(), 1):
        label = _label_for(key)
        severity = section_severity.get(key, 'info')
        badge = _get_severity_badge(severity).split()[0]  # Just emoji
        # Use standard markdown link without color
        lines.append(f"{i}. {badge} **{label}**")
    lines.append("")
    
    # Section Generation Coverage (simplified without table for ReactMarkdown compatibility)
    lines.append("## ✅ Generation Coverage")
    lines.append("")
    lines.append("**Source Types:** ✅/🎯 Narratives • 📋 Standards • 🎯📋 Narratives+Standards • 🤖 AI Generated")
    lines.append("")
    for key in grouped.keys():
        label = _label_for(key)
        source = narrative_sources.get(key, 'summary')
        score = quality_scores.get(key, 0.5)
        severity = section_severity.get(key, 'info')
        
        source_text = source.replace('_', ' ').title()
        if source == 'verified_narrative':
            source_text = f"✅ Verified Narrative"
        elif source == 'building_code_enhanced':
            source_text = f"📋 Building Code-Enhanced"
        elif source == 'ai_generated':
            source_text = f"🤖 AI Generated"
        elif source == 'reranked_narrative':
            source_text = f"🎯 Reranked Narrative"
        
        severity_badge = _get_severity_badge(severity).split()[0]  # Just emoji
        lines.append(f"- **{label}**: {source_text} ({score:.0%}) {severity_badge}")
    lines.append("")
    
    # Process each section
    client = None
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        client = OpenAI(api_key=api_key)
    
    for key, clips in grouped.items():
        label = _label_for(key)
        severity = section_severity.get(key, 'info')
        source = narrative_sources.get(key, 'summary')
        score = quality_scores.get(key, 0.5)
        
        # Section header with badges
        lines.append(f"## {label}")
        lines.append(f"{_get_severity_badge(severity)} • {_get_source_badge(source, score)}")
        lines.append("")
        
        # Professional summary
        try:
            if client:
                ctx = "\n\n".join([c.get('transcript') or '' for c in clips if c.get('transcript')])[:4000]
                if ctx.strip():
                    prompt = """You are drafting a professional section summary for a home inspection report. 
                    Tone: objective, professional, informative. 2-3 sentences maximum.
                    Focus on condition assessment and recommendations.
                    IMPORTANT: Do NOT use tables or pipe characters (|). Use only plain text."""
                    
                    resp = client.chat.completions.create(
                        model='gpt-4o-mini',
                        temperature=0.2,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Section: {label}\nFindings:\n{ctx}"}
                        ],
                    )
                    summary = (resp.choices[0].message.content or '').strip()
                    if summary:
                        lines.append(f"### Summary")
                        lines.append(summary)
                        lines.append("")
        except Exception:
            pass
        
        # Professional Findings from narratives
        narratives = narratives_by_section.get(key, [])
        if narratives:
            lines.append("### Findings & Recommendations")
            for i, narrative in enumerate(narratives[:3], 1):
                text = narrative.get('text', '').strip()
                if text:
                    # Check if it's RAG-enhanced
                    if narrative.get('rag_enhanced'):
                        lines.append(f"{i}. 📋 {text}")
                    elif narrative.get('generated'):
                        lines.append(f"{i}. 🤖 {text}")
                    else:
                        lines.append(f"{i}. {text}")
            lines.append("")
        
        # Inspection Notes (Observations)
        lines.append("### Inspection Notes")
        for c in clips:
            tid = c.get('id')
            tr = (c.get('transcript') or '').strip()
            if tr:
                first = re.split(r"(?<=[.!?])\s+", tr)[0]
                lines.append(f"- {first} *(Clip {tid})*")
            
            # Enhanced photo gallery
            photos = c.get('photos') or []
            if photos:
                lines.append("  ")
                lines.append("  **Photos:**")
                for ph in photos:
                    url = ph.get('url')
                    cap = (ph.get('user_caption') or '').strip()
                    if url:
                        if cap:
                            lines.append(f"  - ![{cap}]({url})")
                        else:
                            lines.append(f"  - ![Photo]({url})")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Record enhanced section metadata
        section_meta[key] = {
            'generationMode': source,
            'severity': severity,
            'qualityScore': score,
            'narrativeCount': len(narratives),
            'hasRagEnhancement': source == 'building_code_enhanced',
            'clipCount': len(clips),
            'photoCount': sum(len(c.get('photos', [])) for c in clips)
        }
    
    # Footer with metadata
    lines.append("## 📝 Report Metadata")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **Quality Score:** {report_quality:.0%}")
    lines.append(f"- **Sections:** {section_count}")
    lines.append(f"- **Observations:** {clip_count}")
    # Determine version based on Cohere availability
    has_cohere = bool(os.getenv('COHERE_API_KEY', '').strip())
    version_display = "2.1 Reranker" if has_cohere else "2.0 Enhanced"
    lines.append(f"- **Report Version:** {version_display}")
    lines.append("")
    
    markdown = "\n".join(lines).strip() + "\n"
    
    # Final sanitization: Remove any pipe characters that might cause ReactMarkdown issues
    # Replace pipe characters with bullet points or dashes
    markdown = markdown.replace(" | ", " • ")
    markdown = markdown.replace("|", "•")
    
    return markdown, section_count, clip_count, section_meta, executive_summary, report_quality


def node_save_draft(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    markdown = state.get("markdown", "")
    saved = False
    app_mod = _get_app_mod()
    if app_mod.admin_db and markdown:
        try:
            if os.getenv("REPORT_LOGS") == "1":
                keys = list((state.get('section_metadata') or {}).keys())
                print(f"[report] save_draft: section_metadata_keys={keys}")
            
            # Enhanced save with more metadata
            app_mod.admin_db.collection('inspections').document(inspection_id).collection('reports').document('draft').set({
                'markdown': markdown,
                'generatedAt': app_mod.admin_firestore.SERVER_TIMESTAMP,  # type: ignore[attr-defined]
                'sectionCount': state.get('section_count', 0),
                'clipCount': state.get('clip_count', 0),
                'usedNarratives': bool(state.get('narratives_by_section')),
                'sectionMetadata': state.get('section_metadata') or {},
                'executiveSummary': state.get('executive_summary', ''),
                'reportQualityScore': state.get('report_quality_score', 0.5),
                'narrativeSources': state.get('narrative_sources', {}),
                'version': '2.0_enhanced'
            }, merge=True)
            saved = True
            
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] Report saved successfully with quality score: {state.get('report_quality_score', 0):.0%}")
        except Exception as e:
            if os.getenv("REPORT_LOGS") == "1":
                print(f"[report] Save error: {e}")
            saved = False
    state["saved"] = saved
    return state


def build_enhanced_report_graph():
    """Build the enhanced report generation graph with fallback loop"""
    g = StateGraph(ReportState)
    
    # Add nodes
    g.add_node("load_data", node_load_data)
    g.add_node("group_by_section", node_group_by_section)
    g.add_node("retrieve_narratives_with_fallback", node_retrieve_narratives_with_fallback)
    g.add_node("assemble_enhanced_markdown", node_assemble_enhanced_markdown)
    g.add_node("save_draft", node_save_draft)
    
    # Define edges
    g.add_edge(START, "load_data")
    g.add_edge("load_data", "group_by_section")
    g.add_edge("group_by_section", "retrieve_narratives_with_fallback")
    g.add_edge("retrieve_narratives_with_fallback", "assemble_enhanced_markdown")
    g.add_edge("assemble_enhanced_markdown", "save_draft")
    g.add_edge("save_draft", END)
    
    return g.compile()


@traceable(name="run_enhanced_report")
def run_enhanced_report(inspection_id: str, sections: Optional[List[str]] = None) -> Dict:
    """Run the enhanced report generation with intelligent fallback"""
    graph = build_enhanced_report_graph()
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
        "version": "2.0_enhanced"
    }


# Helper functions from original (unchanged)
def _load_report_sections() -> List[Dict]:
    try:
        base_api = os.path.dirname(__file__)
        env_path = os.getenv('REPORT_SECTIONS_PATH')
        if env_path and os.path.exists(env_path):
            yaml_path = env_path
        else:
            preferred_yaml = os.path.join(base_api, 'config', 'report_sections.yaml')
            legacy_local = os.path.join(base_api, 'report_sections.yaml')
            if os.path.exists(preferred_yaml):
                yaml_path = preferred_yaml
            elif os.path.exists(legacy_local):
                yaml_path = legacy_local
            else:
                raise FileNotFoundError("report_sections.yaml not found")
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f) or {}
        sections = data.get('sections') or []
        out = []
        for s in sections:
            key = (s.get('key') or '').strip()
            label = (s.get('label') or key).strip()
            includes = s.get('includes') or []
            inc = [str(x) for x in includes if isinstance(x, (str, int, float))]
            if key:
                out.append({'key': key, 'label': label, 'includes': inc})
        return out
    except Exception:
        return []


def _collect_inspection_data(inspection_id: str) -> Tuple[List[Dict], int, Dict]:
    app_mod = _get_app_mod()
    items: List[Dict] = []
    total = 0
    inspection_meta = {}
    if getattr(app_mod, 'admin_db', None):
        try:
            # Fetch inspection metadata
            insp_doc = app_mod.admin_db.collection('inspections').document(inspection_id).get()
            if insp_doc.exists:
                inspection_meta = insp_doc.to_dict() or {}
            
            # Fetch clips
            clip_docs = list(app_mod.admin_db.collection('inspections').document(inspection_id).collection('clips').stream())
            for cd in clip_docs:
                data = cd.to_dict() or {}
                if not (data.get('audioUrl') or data.get('audio_url')):
                    continue
                total += 1
                items.append({
                    'id': cd.id,
                    'section': data.get('section') or '',
                    'transcript': data.get('transcript') or '',
                    'photos': data.get('photos') or [],
                    'status': data.get('status') or '',
                })
            return items, total, inspection_meta
        except Exception:
            pass
    return items, total, inspection_meta