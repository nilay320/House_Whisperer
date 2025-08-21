#!/usr/bin/env python3
"""
Generate a mapping from narrative sections (CSV "Section Name") → report sections (YAML keys)

Terminology:
- narrative section: from docs/reference/narratives.csv → column "Section Name"
- report section: canonical section key from api/config/report_sections.yaml (used by the UI and clips)

Output JSON (default: scripts/config/narratives_to_report_section_map.json):
{
  "report_section_keys": [ ... ],
  "narrative_section_names": [ ... ],
  "mapping": {
    "<narrative_section_slug>": {
      "narrative_section_name": "...",
      "report_section_key": "<yaml_key or UNMAPPED>",
      "method": "exact_key|exact_label|alias|token|semantic|fuzzy|unmapped",
      "similarity": 0.0,
      "token_overlap": 0.0,
      "alternates": [ {"report_section_key": "...", "similarity": 0.0 } ]
    },
    ...
  }
}

Strategy (high precision → high recall):
1) exact YAML key slug; 2) exact YAML label slug; 3) alias file; 4) token overlap; 5) semantic cosine; 6) fuzzy; else UNMAPPED.

Usage:
  export OPENAI_API_KEY=...   # only if using semantic
  python scripts/generate_narratives_to_report_map.py \
    --csv docs/reference/narratives.csv \
    --yaml api/config/report_sections.yaml \
    --out scripts/config/narratives_to_report_section_map.json \
    --use-embeddings 1
"""

import argparse
import csv
import difflib
import json
import math
import os
import re
from typing import Dict, List, Tuple

try:
    import yaml  # PyYAML
except Exception:
    raise SystemExit("ERROR: PyYAML not installed. `pip install PyYAML`")

try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


def slugify(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def tokens(slug: str) -> List[str]:
    return [t for t in slug.split("_") if t]


def jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def load_yaml_sections(path_primary: str, path_fallback: str) -> List[Dict]:
    path = path_primary if os.path.exists(path_primary) else path_fallback
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sections") or []


def load_csv_sections(csv_path: str) -> List[str]:
    out: List[str] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sec = (row.get("Section Name") or "").strip()
            if sec:
                out.append(sec)
    # unique preserve order
    seen = set()
    uniq: List[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def build_maps(yaml_sections: List[Dict]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return (key_slug_to_key, label_slug_to_key)."""
    key_slug_to_key: Dict[str, str] = {}
    label_slug_to_key: Dict[str, str] = {}
    for s in yaml_sections:
        key = (s.get("key") or "").strip()
        label = (s.get("label") or key).strip()
        if key:
            key_slug = slugify(key)
            key_slug_to_key[key_slug] = key
            label_slug = slugify(label)
            label_slug_to_key[label_slug] = key
    return key_slug_to_key, label_slug_to_key


def cosine(a: List[float], b: List[float]) -> float:
    num = sum(x*y for x, y in zip(a, b))
    da = math.sqrt(sum(x*x for x in a))
    db = math.sqrt(sum(y*y for y in b))
    return (num / (da*db)) if da and db else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate narrative→report section map (with optional semantic matching)")
    parser.add_argument("--csv", default="docs/reference/narratives.csv", help="Path to narratives.csv")
    parser.add_argument("--yaml", default="api/config/report_sections.yaml", help="Path to YAML sections (primary)")
    parser.add_argument("--yaml-fallback", default="docs/plan/report-writer/report_sections.yaml", help="Fallback YAML path")
    parser.add_argument("--alias", default="", help="Optional JSON file with narrative_slug→report_key aliases")
    parser.add_argument("--out", default="scripts/config/narratives_to_report_section_map.json", help="Output JSON path")
    parser.add_argument("--use-embeddings", type=int, default=1, help="Use OpenAI embeddings for semantic matching (1/0)")
    parser.add_argument("--embed-model", default="text-embedding-3-small", help="OpenAI embeddings model")
    parser.add_argument("--accept-cos", type=float, default=0.85, help="Cosine threshold for semantic accept")
    parser.add_argument("--accept-cos-soft", type=float, default=0.70, help="Soft cosine threshold")
    parser.add_argument("--accept-token-soft", type=float, default=0.30, help="Token overlap needed with soft cosine")
    parser.add_argument("--fuzzy-cutoff", type=float, default=0.60, help="difflib cutoff for fuzzy match")
    parser.add_argument("--alt-margin", type=float, default=0.03, help="Alternates within this cosine margin of top-1 are listed")
    args = parser.parse_args()

    yaml_sections = load_yaml_sections(args.yaml, args.yaml_fallback)
    csv_secs = load_csv_sections(args.csv)
    key_slug_to_key, label_slug_to_key = build_maps(yaml_sections)

    alias_map: Dict[str, str] = {}
    if args.alias and os.path.exists(args.alias):
        try:
            with open(args.alias, "r", encoding="utf-8") as af:
                raw_alias = json.load(af)
            alias_map = {slugify(k): v for k, v in raw_alias.items()}
        except Exception as e:
            print(f"⚠️ Failed to load alias file {args.alias}: {e}")

    # Prepare YAML target strings for semantic matching
    yaml_targets: List[str] = []
    yaml_target_keys: List[str] = []
    if args.use_embeddings and _OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        for s in yaml_sections:
            key = (s.get("key") or "").strip()
            label = (s.get("label") or key).strip()
            inc = s.get("includes") or []
            inc_str = ", ".join([str(x) for x in inc]) if inc else ""
            target = f"{key} — {label} — includes: {inc_str}".strip()
            yaml_targets.append(target)
            yaml_target_keys.append(key)
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        try:
            emb = client.embeddings.create(model=args.embed_model, input=yaml_targets)
            yaml_vecs = [d.embedding for d in emb.data]
        except Exception as e:
            print(f"⚠️ Embedding YAML targets failed ({e}); continuing without semantic matching")
            yaml_vecs = []
            args.use_embeddings = 0  # disable
    else:
        yaml_vecs = []

    # Precompute token sets
    yaml_key_tokens = {slug: tokens(slug) for slug in key_slug_to_key.keys()}
    yaml_label_tokens = {slug: tokens(slug) for slug in label_slug_to_key.keys()}

    mapping: Dict[str, Dict] = {}

    for csv_name in csv_secs:
        csv_slug = slugify(csv_name)

        # 1) exact YAML key slug
        if csv_slug in key_slug_to_key:
            mapping[csv_slug] = {
                "narrative_section_name": csv_name,
                "report_section_key": key_slug_to_key[csv_slug],
                "method": "exact_key",
                "similarity": 1.0,
                "token_overlap": 1.0,
            }
            continue

        # 2) exact YAML label slug
        if csv_slug in label_slug_to_key:
            mapping[csv_slug] = {
                "narrative_section_name": csv_name,
                "report_section_key": label_slug_to_key[csv_slug],
                "method": "exact_label",
                "similarity": 1.0,
                "token_overlap": 1.0,
            }
            continue

        # 3) alias file
        alias = alias_map.get(csv_slug)
        if alias and alias in key_slug_to_key.values():
            mapping[csv_slug] = {
                "narrative_section_name": csv_name,
                "report_section_key": alias,
                "method": "alias",
                "similarity": 1.0,
                "token_overlap": 1.0,
            }
            continue

        # 4) token overlap
        csv_toks = tokens(csv_slug)
        best = (0.0, None, "")  # score, report_key, source
        for slug, toks in yaml_key_tokens.items():
            sc = jaccard(csv_toks, toks)
            if sc > best[0]:
                best = (sc, key_slug_to_key[slug], "token_key")
        for slug, toks in yaml_label_tokens.items():
            sc = jaccard(csv_toks, toks)
            if sc > best[0]:
                best = (sc, label_slug_to_key[slug], "token_label")
        if best[0] >= 0.50:
            mapping[csv_slug] = {
                "narrative_section_name": csv_name,
                "report_section_key": best[1],
                "method": best[2],
                "similarity": 0.0,
                "token_overlap": round(best[0], 3),
            }
            continue

        # 5) semantic similarity
        if args.use_embeddings and yaml_vecs:
            try:
                emb_csv = client.embeddings.create(model=args.embed_model, input=[csv_name])
                v = emb_csv.data[0].embedding
                scores = [cosine(v, yv) for yv in yaml_vecs]
                top_idx = max(range(len(scores)), key=lambda i: scores[i]) if scores else -1
                top_cos = scores[top_idx] if top_idx >= 0 else 0.0
                alts = []
                for i, sc in enumerate(scores):
                    if i == top_idx:
                        continue
                    if top_cos - sc <= args.alt_margin:
                        alts.append({"report_section_key": yaml_target_keys[i], "similarity": round(sc, 3)})
                if top_cos >= args.accept_cos or (top_cos >= args.accept_cos_soft and best[0] >= args.accept_token_soft):
                    mapping[csv_slug] = {
                        "narrative_section_name": csv_name,
                        "report_section_key": yaml_target_keys[top_idx] if top_idx >= 0 else "UNMAPPED",
                        "method": "semantic",
                        "similarity": round(top_cos, 3),
                        "token_overlap": round(best[0], 3),
                        "alternates": alts,
                    }
                    continue
            except Exception as e:
                print(f"⚠️ Semantic match failed for '{csv_name}': {e}")

        # 6) fuzzy fallback on slugs
        candidates = list(key_slug_to_key.keys()) + list(label_slug_to_key.keys())
        close = difflib.get_close_matches(csv_slug, candidates, n=1, cutoff=args.fuzzy_cutoff)
        if close:
            slug = close[0]
            report_key = key_slug_to_key.get(slug) or label_slug_to_key.get(slug)
            mapping[csv_slug] = {
                "narrative_section_name": csv_name,
                "report_section_key": report_key,
                "method": "fuzzy",
                "similarity": 0.9,
                "token_overlap": round(best[0], 3),
            }
            continue

        # 7) unmapped
        mapping[csv_slug] = {
            "narrative_section_name": csv_name,
            "report_section_key": "UNMAPPED",
            "method": "unmapped",
            "similarity": 0.0,
            "token_overlap": round(best[0], 3),
        }

    out = {
        "report_section_keys": [s.get("key") for s in yaml_sections if s.get("key")],
        "narrative_section_names": csv_secs,
        "mapping": mapping,
        "instructions": (
            "Review report_section_key values. Replace any 'UNMAPPED' with a valid YAML key from api/report_sections.yaml."
        ),
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Wrote mapping to {args.out}")

    # Echo unmapped list for convenience
    unmapped = [v["narrative_section_name"] for v in mapping.values() if v.get("report_section_key") == "UNMAPPED"]
    if unmapped:
        print("\nUNMAPPED narrative sections (edit the JSON to resolve):")
        for name in unmapped:
            print(" -", name)
    else:
        print("All narrative sections mapped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


