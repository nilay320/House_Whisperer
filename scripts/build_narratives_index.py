#!/usr/bin/env python3
"""
Build a Qdrant collection from docs/reference/narratives.csv

- Embeds each narrative (Comment Name + Comment Text) with OpenAI `text-embedding-3-small`
- Upserts into Qdrant with payload metadata

Env vars required:
  - OPENAI_API_KEY
  - QDRANT_URL
  - QDRANT_API_KEY

Usage:
  python scripts/build_narratives_index.py \
    --csv docs/reference/narratives.csv \
    --collection narratives_v1 \
    --dim 1536 \
    --batch-size 64

Notes:
  - Section key is normalized to lowercase slug (letters/digits/underscores)
  - Point id is a stable 64-bit int hash of section+comment_name
"""

import argparse
import csv
import json
import hashlib
import os
import re
import sys
from typing import List, Dict

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
except Exception as e:  # pragma: no cover
    print("ERROR: qdrant-client is not installed. `pip install qdrant-client`", file=sys.stderr)
    raise

try:
    from openai import OpenAI
except Exception:
    print("ERROR: openai is not installed. `pip install openai`", file=sys.stderr)
    raise


def normalize_section_key(section_name: str) -> str:
    s = (section_name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "general"


def stable_point_id(section_key: str, comment_name: str, comment_text: str) -> int:
    base = f"{section_key}::{comment_name}::{comment_text}".encode("utf-8", errors="ignore")
    h = hashlib.sha1(base).hexdigest()  # 40 hex chars
    # Fit into signed 64-bit
    return int(h[:16], 16) & 0x7FFF_FFFF_FFFF_FFFF


def chunked(seq: List[str], size: int) -> List[List[str]]:
    return [seq[i:i+size] for i in range(0, len(seq), size)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Qdrant index for narratives.csv")
    parser.add_argument("--csv", default="docs/reference/narratives.csv", help="Path to narratives.csv")
    parser.add_argument("--collection", default="narratives_v1", help="Qdrant collection name")
    parser.add_argument("--dim", type=int, default=1536, help="Vector size for embeddings model")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embeddings model")
    parser.add_argument("--map", default="scripts/config/narratives_to_report_section_map.json", help="JSON mapping: narrative section (CSV) → report section key (YAML)")
    args = parser.parse_args()

    openai_key = os.getenv("OPENAI_API_KEY")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY is not set", file=sys.stderr)
        return 1
    if not qdrant_url or not qdrant_key:
        print("ERROR: QDRANT_URL / QDRANT_API_KEY are not set", file=sys.stderr)
        return 1

    # Load narrative→report section mapping (optional, recommended)
    mapping: Dict[str, str] = {}
    if os.path.exists(args.map):
        try:
            with open(args.map, "r", encoding="utf-8") as mf:
                raw = json.load(mf)
            # Accept either a flat dict {narrative_slug: report_key} or an object with "mapping": {...}
            if isinstance(raw, dict) and "mapping" in raw and isinstance(raw["mapping"], dict):
                for k, v in raw["mapping"].items():
                    # Support nested { yaml_key: ... } shape
                    if isinstance(v, dict):
                        if "yaml_key" in v:
                            mapping[normalize_section_key(k)] = str(v["yaml_key"]).strip()
                        elif "report_section_key" in v:
                            mapping[normalize_section_key(k)] = str(v["report_section_key"]).strip()
                        else:
                            # try common field names
                            for cand in ("report", "key"):
                                if cand in v and isinstance(v[cand], str) and v[cand].strip():
                                    mapping[normalize_section_key(k)] = v[cand].strip()
                                    break
                    else:
                        mapping[normalize_section_key(k)] = str(v).strip()
            elif isinstance(raw, dict):
                for k, v in raw.items():
                    mapping[normalize_section_key(k)] = str(v).strip()
            print(f"Loaded narrative→report mapping with {len(mapping)} entries from {args.map}")
        except Exception as e:
            print(f"⚠️ Failed to load mapping {args.map}: {e}. Proceeding without explicit map.")
    else:
        print(f"⚠️ Mapping file not found at {args.map}. Proceeding without explicit map.")

    # Load CSV
    rows: List[Dict] = []
    with open(args.csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            section_name = (r.get("Section Name") or "").strip()
            item_name = (r.get("Item Name") or "").strip()
            comment_name = (r.get("Comment Name") or "").strip()
            comment_text = (r.get("Comment Text") or "").strip()
            comment_type = (r.get("Comment Type (info, limit, defect)") or "").strip()
            category = (r.get("Category (-1: Low, 0: Med, 1: High)") or "").strip()
            recommendation = (r.get("Recommendation (from list)") or "").strip()
            if not (section_name and (comment_name or comment_text)):
                continue
            narrative_section_slug = normalize_section_key(section_name)
            # Resolve to canonical report section key using the provided mapping when available
            report_section_key = mapping.get(narrative_section_slug, "")
            text = f"{comment_name}. {comment_text}".strip(". ")
            rows.append({
                "narrative_section_slug": narrative_section_slug,
                "report_section_key": report_section_key,  # may be empty if not mapped
                "section_name": section_name,
                "item_name": item_name,
                "comment_name": comment_name,
                "comment_text": comment_text,
                "comment_type": comment_type,
                "category": category,
                "recommendation": recommendation,
                "text": text or comment_name or comment_text,
            })

    if not rows:
        print("No usable rows found in CSV.")
        return 0

    # Initialize clients
    client = OpenAI(api_key=openai_key)
    qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_key)

    # Ensure collection exists
    try:
        qdrant.get_collection(args.collection)
    except Exception:
        qdrant.recreate_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=args.dim, distance=Distance.COSINE),
        )

    # Embed + upsert in batches
    texts = [r["text"] for r in rows]
    points: List[PointStruct] = []
    total_upserted = 0

    unmapped_count = 0
    for batch_rows in chunked(rows, args.batch_size):
        batch_texts = [br["text"] for br in batch_rows]
        emb = client.embeddings.create(model=args.model, input=batch_texts)
        vectors = [d.embedding for d in emb.data]
        for br, vec in zip(batch_rows, vectors):
            # Prefer the canonical report section key; if missing, fall back to the narrative slug (will be less precise at query time)
            section_for_payload = br["report_section_key"] or br["narrative_section_slug"]
            if not br["report_section_key"]:
                unmapped_count += 1
            pid = stable_point_id(section_for_payload, br["comment_name"], br["comment_text"])
            payload = {
                # payload.section is the canonical report section key (YAML) when mapping is provided;
                # otherwise it falls back to the narrative section slug (CSV)
                "section": section_for_payload,
                "section_report": br["report_section_key"] or None,
                "section_narrative": br["narrative_section_slug"],
                "section_name": br["section_name"],
                "item_name": br["item_name"],
                "comment_name": br["comment_name"],
                "comment_text": br["comment_text"],
                "comment_type": br["comment_type"],
                "category": br["category"],
                "recommendation": br["recommendation"],
            }
            points.append(PointStruct(id=pid, vector=vec, payload=payload))

        # Upsert incrementally to avoid huge payloads
        if points:
            qdrant.upsert(collection_name=args.collection, points=points)
            total_upserted += len(points)
            print(f"Upserted {total_upserted} points so far...")
            points = []

    if unmapped_count:
        print(f"⚠️ {unmapped_count} narratives had no mapping; payload.section fell back to narrative section slug. Provide --map to normalize.")
    print("Done. Collection:", args.collection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


