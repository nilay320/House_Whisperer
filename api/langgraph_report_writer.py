from typing import TypedDict, Optional, List, Dict
import os, re, yaml
from datetime import datetime
from openai import OpenAI

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
    sections_catalog: List[Dict]
    narratives_by_section: Dict[str, List[Dict]]
    # Grouped
    grouped: Dict[str, List[Dict]]
    # Output
    markdown: str
    section_count: int
    clip_count: int
    saved: bool


def node_load_data(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    clips, _ = _collect_inspection_data(inspection_id)
    sections_catalog = _load_report_sections()
    narratives_by_section = {}  # minimal v1: omit narratives inside writer
    state.update({
        "clips": clips,
        "sections_catalog": sections_catalog,
        "narratives_by_section": narratives_by_section,
    })
    return state


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
        # Leave empty; caller can decide to error out
        grouped = {}
    state["grouped"] = grouped
    return state


def node_assemble_markdown(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    grouped = state.get("grouped", {})
    sections_catalog = state.get("sections_catalog", [])
    narratives_by_section = state.get("narratives_by_section", {})
    markdown, section_count, clip_count = _render_markdown(inspection_id, grouped, sections_catalog, narratives_by_section)
    state.update({
        "markdown": markdown,
        "section_count": section_count,
        "clip_count": clip_count,
    })
    return state


def node_save_draft(state: ReportState) -> ReportState:
    inspection_id = state["inspection_id"]
    markdown = state.get("markdown", "")
    saved = False
    app_mod = _get_app_mod()
    if app_mod.admin_db and markdown:
        try:
            app_mod.admin_db.collection('inspections').document(inspection_id).collection('reports').document('draft').set({
                'markdown': markdown,
                'generatedAt': app_mod.admin_firestore.SERVER_TIMESTAMP,  # type: ignore[attr-defined]
                'sectionCount': state.get('section_count', 0),
                'clipCount': state.get('clip_count', 0),
                'usedNarratives': bool(state.get('narratives_by_section')),
            }, merge=True)
            saved = True
        except Exception:
            saved = False
    state["saved"] = saved
    return state


def build_report_graph():
    g = StateGraph(ReportState)
    g.add_node("load_data", node_load_data)
    g.add_node("group_by_section", node_group_by_section)
    g.add_node("assemble_markdown", node_assemble_markdown)
    g.add_node("save_draft", node_save_draft)

    g.add_edge(START, "load_data")
    g.add_edge("load_data", "group_by_section")
    g.add_edge("group_by_section", "assemble_markdown")
    g.add_edge("assemble_markdown", "save_draft")
    g.add_edge("save_draft", END)
    return g.compile()


def run_report(inspection_id: str, sections: Optional[List[str]] = None) -> Dict:
    graph = build_report_graph()
    initial: ReportState = {"inspection_id": inspection_id, "sections_filter": sections or []}
    out: ReportState = graph.invoke(initial)  # type: ignore
    return {
        "markdown": out.get("markdown", ""),
        "sectionCount": out.get("section_count", 0),
        "clipCount": out.get("clip_count", 0),
        "saved": out.get("saved", False),
    }


# ----------------- Minimal helpers (self-contained) -----------------
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
                raise FileNotFoundError("report_sections.yaml not found; expected at api/config/report_sections.yaml or set REPORT_SECTIONS_PATH")
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


def _collect_inspection_data(inspection_id: str) -> (List[Dict], int):
    app_mod = _get_app_mod()
    items: List[Dict] = []
    total = 0
    if getattr(app_mod, 'admin_db', None):
        try:
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
            return items, total
        except Exception:
            pass
    # Fallback empty
    return items, total


def _render_markdown(inspection_id: str, grouped: Dict[str, List[Dict]], sections_catalog: List[Dict], narratives_by_section: Dict) -> (str, int, int):
    def _label_for(key: str) -> str:
        for s in sections_catalog:
            if s.get('key') == key:
                return s.get('label') or key
        return key

    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    section_count = len(grouped)
    clip_count = sum(len(v) for v in grouped.values())
    lines: List[str] = []
    lines.append(f"# Home Inspection Draft Report\n")
    lines.append(f"Generated: {now}\n")
    lines.append(f"Inspection ID: {inspection_id}\n")
    lines.append("")

    client = None
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        client = OpenAI(api_key=api_key)

    for key, clips in grouped.items():
        label = _label_for(key)
        lines.append(f"## {label}\n")
        # Brief summary
        try:
            if client:
                ctx = "\n\n".join([c.get('transcript') or '' for c in clips if c.get('transcript')])[:4000]
                if ctx.strip():
                    prompt = "You are drafting a concise homeowner-friendly section summary for a home inspection report. Tone: objective, non-alarmist. 1-2 sentences. No speculation."
                    resp = client.chat.completions.create(
                        model='gpt-4o-mini',
                        temperature=0.2,
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": f"Section: {label}\nNotes:\n{ctx}"}],
                    )
                    summary = (resp.choices[0].message.content or '').strip()
                    if summary:
                        lines.append(f"**Summary**: {summary}\n")
        except Exception:
            pass

        lines.append("### Observations\n")
        for c in clips:
            tid = c.get('id')
            tr = (c.get('transcript') or '').strip()
            if tr:
                first = re.split(r"(?<=[.!?])\s+", tr)[0]
                lines.append(f"- Transcript note (clip {tid}): {first}")
            else:
                lines.append(f"- Clip {tid}: (no transcript yet)")
            photos = c.get('photos') or []
            for ph in photos:
                cap = (ph.get('user_caption') or '').strip()
                url = ph.get('url')
                if url:
                    # Emit Markdown image so renderers can inline it; keep as a bullet
                    safe_cap = cap if cap else ''
                    lines.append(f"  - ![{safe_cap}]({url})")
        lines.append("")

    markdown = "\n".join(lines).strip() + "\n"
    return markdown, section_count, clip_count



