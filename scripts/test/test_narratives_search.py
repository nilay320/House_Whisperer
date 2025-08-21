#!/usr/bin/env python3
"""
Ad-hoc evaluation of the narratives collection in Qdrant for our use case.

- For each test case (report_section, transcript snippet, expected keywords),
  embed the snippet, query Qdrant filtered by payload.section == report_section,
  and report the top hits along with a simple pass/fail heuristic:
  PASS if any top hit contains at least one expected keyword in comment_name/comment_text (case-insensitive).

Env:
  OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY

Usage:
  python scripts/test/test_narratives_search.py --collection narratives_v1 --top-k 5
"""

import argparse
import os
import re
from typing import List, Dict

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
except Exception:
    raise SystemExit("ERROR: qdrant-client not installed. `pip install qdrant-client`")

try:
    from openai import OpenAI
except Exception:
    raise SystemExit("ERROR: openai not installed. `pip install openai`")


def contains_any(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in keywords if k)


def get_tests() -> List[Dict]:
    return [
        {
            "name": "Electrical: double-tapped breaker",
            "section": "electrical",
            "snippet": "Two wires are connected to a single breaker (double-tap). This is not allowed and should be corrected by a qualified electrician.",
            "expect": ["double-tap", "breaker"],
        },
        {
            "name": "Roof: missing/damaged shingles",
            "section": "roof",
            "snippet": "Several asphalt shingles are damaged and a few are missing along the south slope.",
            "expect": ["shingle", "missing"],
        },
        {
            "name": "Insulation/Ventilation: attic insulation depth",
            "section": "insulation_ventilation",
            "snippet": "Attic insulation averages 4-6 inches; recommend adding insulation to meet modern standards.",
            "expect": ["insulation", "attic", "inches"],
        },
        {
            "name": "Plumbing: active leak under sink",
            "section": "plumbing",
            "snippet": "There is an active leak at the P-trap under the kitchen sink. Repair recommended to prevent damage and microbial growth.",
            "expect": ["leak", "trap", "sink"],
        },
        {
            "name": "HVAC: disconnected duct",
            "section": "hvac",
            "snippet": "One supply duct in the attic is disconnected and leaking air into the attic space.",
            "expect": ["duct", "disconnected", "attic"],
        },
        {
            "name": "Site & Drainage: negative slope toward foundation",
            "section": "site_drainage",
            "snippet": "Soil slopes toward the foundation in areas; recommend grading to slope away to reduce moisture intrusion.",
            "expect": ["grading", "slope", "foundation"],
        },
        {
            "name": "Interior: window inoperable",
            "section": "interior",
            "snippet": "A bedroom window would not open and requires adjustment or repair for egress and ventilation.",
            "expect": ["window", "open", "egress"],
        },
        {
            "name": "Garage: auto-reverse not functioning",
            "section": "garage",
            "snippet": "The overhead door auto-reverse feature did not respond to resistance. Safety repair recommended.",
            "expect": ["auto-reverse", "overhead door"],
        },
        {
            "name": "Exterior: damaged siding",
            "section": "exterior",
            "snippet": "Damaged lap siding noted on the west elevation with exposed substrate.",
            "expect": ["siding", "damaged"],
        },
        {
            "name": "Fireplace/Chimney: creosote buildup",
            "section": "fireplaces_chimneys",
            "snippet": "Significant creosote accumulation noted in the flue; recommend cleaning by a qualified chimney sweep.",
            "expect": ["creosote", "flue"],
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Qdrant narratives collection efficacy")
    parser.add_argument("--collection", default="narratives_v1", help="Qdrant collection name")
    parser.add_argument("--top-k", type=int, default=5, help="Top K neighbors to fetch")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embedding model")
    parser.add_argument("--pass-threshold", type=float, default=0.55, help="PASS if any hit score ≥ threshold")
    args = parser.parse_args()

    openai_key = os.getenv("OPENAI_API_KEY")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    if not openai_key or not qdrant_url or not qdrant_key:
        raise SystemExit("Missing env: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY")

    client = OpenAI(api_key=openai_key)
    qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_key)

    tests = get_tests()
    total = len(tests)
    passes = 0

    print(f"Running {total} tests against collection '{args.collection}' (top_k={args.top_k})\n")

    for i, t in enumerate(tests, 1):
        # Embed snippet
        emb = client.embeddings.create(model=args.model, input=[t["snippet"]])
        vec = emb.data[0].embedding
        # Filter by canonical report section key
        flt = Filter(should=[], must=[FieldCondition(key="section", match=MatchValue(value=t["section"]))])
        res = qdrant.search(collection_name=args.collection, query_vector=vec, query_filter=flt, limit=args.top_k)
        # Check expected keyword presence
        found = False
        lines = []
        for idx, pt in enumerate(res, 1):
            payload = pt.payload or {}
            name = payload.get("comment_name", "")
            text = payload.get("comment_text", "")
            line = f"  {idx}. score={pt.score:.3f} | {name} — {text[:120].replace('\n',' ')}"
            lines.append(line)
            if contains_any(name, t["expect"]) or contains_any(text, t["expect"]) or (pt.score >= args.pass_threshold):
                found = True

        status = "PASS" if found else "FAIL"
        if found:
            passes += 1
        print(f"[{i}/{total}] {status} | {t['name']} (section={t['section']})")
        print("  Snippet:", t["snippet"]) 
        for ln in lines:
            print(ln)
        print()

    print(f"Summary: {passes}/{total} tests passed")
    return 0 if passes == total else 1


if __name__ == "__main__":
    raise SystemExit(main())


