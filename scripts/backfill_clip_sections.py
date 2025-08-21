#!/usr/bin/env python3
"""
Backfill missing clip.section values in Firestore using simple heuristics.

Requires env:
- FIREBASE_SERVICE_ACCOUNT_JSON (preferred) or Application Default Credentials

Usage (dry run first):
  python scripts/backfill_clip_sections.py --dry-run

Options:
  --inspection-id <id>   Only process a single inspection
  --default <key>        Fallback section key when no match (default: uncategorized)
  --apply-even-if-present  Also set section when present but not recognized
  --yes                  Non-interactive, apply without prompt
"""

import argparse
import json
import os
import re
import random
from typing import Dict, List, Tuple

import yaml

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception as e:  # pragma: no cover
    print("ERROR: firebase-admin not installed. pip install firebase-admin")
    raise


def load_sections(yaml_path: str) -> List[Dict]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sections") or []


def build_keyword_index(sections: List[Dict]) -> Dict[str, List[str]]:
    """Return mapping: section_key -> list of lowercase keywords/synonyms."""
    index: Dict[str, List[str]] = {}
    # Base from YAML
    for s in sections:
        key = (s.get("key") or "").strip()
        label = (s.get("label") or key).lower()
        includes = [str(x).lower() for x in (s.get("includes") or [])]
        tokens = set()
        for t in [label] + includes:
            for w in re.split(r"[^a-z0-9]+", t):
                w = w.strip()
                if len(w) >= 3:
                    tokens.add(w)
        index[key] = sorted(tokens)

    # Light manual synonyms that commonly appear in transcripts
    manual: Dict[str, List[str]] = {
        "roof": ["roof", "shingle", "flashing", "soffit", "fascia"],
        "electrical": ["breaker", "panel", "gfci", "afci", "outlet", "receptacle", "wiring"],
        "plumbing": ["leak", "pipe", "piping", "sink", "faucet", "drain", "toilet", "water heater"],
        "hvac": ["furnace", "air handler", "condenser", "heat", "cool", "thermostat"],
        "insulation_ventilation": ["attic", "insulation", "vent", "soffit vent", "ridge vent", "crawlspace"],
        "interior": ["bedroom", "living", "ceiling", "floor", "door", "window", "stair"],
        "exterior": ["siding", "trim", "deck", "porch", "step", "door", "flash"],
        "garage": ["garage", "door opener", "auto reverse"],
        "kitchen": ["kitchen", "cabinet", "counter", "range", "dishwasher"],
        "bathrooms": ["bath", "tub", "shower", "vent fan", "toilet", "vanity"],
        "laundry": ["laundry", "washer", "dryer", "dryer vent"],
        "site_drainage": ["grading", "drainage", "downspout", "slope"],
        "structure": ["foundation", "beam", "joist", "girder", "settlement"],
        "fireplaces_chimneys": ["fireplace", "chimney", "flue", "damper", "gas log"],
    }
    for k, syns in manual.items():
        index.setdefault(k, [])
        for w in syns:
            if w not in index[k]:
                index[k].append(w)
    return index


def score_text(text: str, keywords: List[str]) -> int:
    text = text.lower()
    score = 0
    for kw in keywords:
        if kw and kw in text:
            score += 1
    return score


def infer_section(text: str, index: Dict[str, List[str]]) -> Tuple[str, int]:
    best_key = ""
    best_score = 0
    for key, kws in index.items():
        s = score_text(text, kws)
        if s > best_score:
            best_key, best_score = key, s
    return best_key, best_score


def init_firestore():
    if not getattr(firebase_admin, "_apps", []):
        svc_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if svc_json:
            cred = credentials.Certificate(json.loads(svc_json))
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    return firestore.client()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspection-id", help="Only process a single inspection")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply-even-if-present", action="store_true")
    ap.add_argument("--default", default="uncategorized", help="Fallback section key when no match (use 'random' to pick a random valid section)")
    ap.add_argument("--yes", action="store_true", help="Apply without prompt")
    args = ap.parse_args()

    yaml_path = os.getenv("REPORT_SECTIONS_PATH", os.path.join(os.path.dirname(__file__), "..", "api", "config", "report_sections.yaml"))
    # Normalize path
    yaml_path = os.path.abspath(yaml_path)
    sections = load_sections(yaml_path)
    valid_keys = {s.get("key"): True for s in sections if s.get("key")}
    index = build_keyword_index(sections)

    db = init_firestore()

    inspections = []
    if args.inspection_id:
        inspections = [args.inspection_id]
    else:
        inspections = [d.id for d in db.collection("inspections").stream()]

    updates = []
    scanned = 0
    for insp_id in inspections:
        clips_col = db.collection("inspections").document(insp_id).collection("clips")
        for d in clips_col.stream():
            scanned += 1
            data = d.to_dict() or {}
            current = (data.get("section") or "").strip()
            needs = (not current) or (current not in valid_keys)
            if not needs and not args.apply_even_if_present:
                continue
            txt = (data.get("transcript") or data.get("notes") or "").strip()
            best_key, score = infer_section(txt, index) if txt else ("", 0)
            if score >= 1 and best_key:
                new_key = best_key
            else:
                if args.default == "random" and valid_keys:
                    new_key = random.choice(list(valid_keys.keys()))
                else:
                    new_key = args.default
            if current == new_key:
                continue
            updates.append((insp_id, d.id, current or None, new_key, score))

    if not updates:
        print(f"Nothing to update. Scanned {scanned} clip docs.")
        return 0

    print(f"Planned updates: {len(updates)} (scanned {scanned})")
    for insp_id, clip_id, old, new, score in updates[:20]:
        print(f"  {insp_id}/clips/{clip_id}: {old!r} -> {new!r} (score={score})")
    if len(updates) > 20:
        print(f"  ... {len(updates) - 20} more")

    if args.dry_run:
        print("Dry run mode. No writes performed.")
        return 0

    if not args.yes:
        resp = input("Apply these updates? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return 1

    # Apply
    batch = db.batch()
    cnt = 0
    for insp_id, clip_id, old, new, score in updates:
        ref = db.collection("inspections").document(insp_id).collection("clips").document(clip_id)
        batch.set(ref, {"section": new, "sectionAuto": True}, merge=True)
        cnt += 1
        if cnt % 400 == 0:
            batch.commit()
            batch = db.batch()
    if cnt % 400:
        batch.commit()
    print(f"Applied {cnt} updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


