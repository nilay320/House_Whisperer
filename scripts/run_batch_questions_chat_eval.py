#!/usr/bin/env python3
"""
Batch runner for /api/chat that saves question, answer, sources, and runtime.

Usage:
  python scripts/run_batch_questions_chat_eval.py \
    [--api http://localhost:8000] \
    [--in scripts/questions.txt] \
    [--out scripts/output] \
    [--filesuffix "experiment-tag"]

Outputs:
  - JSONL: scripts/output/batch_results_<ts>[_<filesuffix>].jsonl (one JSON per line)
  - Markdown: scripts/output/batch_results_<ts>[_<filesuffix>].md (human-readable)
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import requests
import re


def read_questions(path: Path | None) -> list[str]:
    if path and path.exists():
        with path.open("r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    # Fallback defaults
    return [
        "What are the NCHILB continuing education requirements?",
        "What are the NC building code requirements for deck railing height?",
        "Best practices for roof inspections according to InterNACHI?",
    ]


def ask(api_url: str, question: str) -> tuple[str, list[dict]]:
    url = f"{api_url.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    payload = {"message": question, "sessionId": f"batch-{int(time.time()*1000)}"}

    answer_chunks: list[str] = []
    sources: list[dict] = []
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data: "):
                continue
            try:
                data = json.loads(raw[6:])
            except json.JSONDecodeError:
                continue
            status = data.get("status")
            if status == "response_chunk":
                answer_chunks.append(data.get("chunk", ""))
            elif status == "sources":
                sources = data.get("sources", [])
            elif status == "complete":
                break
    return ("".join(answer_chunks).strip(), sources)


def to_markdown_row(idx: int, q: str, ans: str, elapsed_ms: int) -> str:
    q_short = q.replace("|", r"\|")
    return f"| {idx} | {elapsed_ms} | {q_short} | {len(ans)} |"


def sanitize_suffix(suffix: str) -> str:
    """Make a human-provided suffix safe for filenames: keep letters, digits, _ and -; replace spaces with -."""
    s = suffix.strip().replace(" ", "-")
    return re.sub(r"[^A-Za-z0-9_\-]", "", s)


def save_outputs(results: list[dict], out_dir: Path, suffix: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    suffix_clean = sanitize_suffix(suffix) if suffix else ""
    tag = f"{ts}" + (f"_{suffix_clean}" if suffix_clean else "")
    jsonl_path = out_dir / f"batch_results_{tag}.jsonl"
    md_path = out_dir / f"batch_results_{tag}.md"

    # JSONL
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Markdown (summary + details)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Batch Results ({datetime.utcnow().isoformat()}Z)\n\n")
        f.write("| # | elapsed_ms | question | answer_len |\n")
        f.write("|---:|----------:|---------|-----------:|\n")
        for i, row in enumerate(results, 1):
            f.write(to_markdown_row(i, row["question"], row["answer"], row["elapsed_ms"]) + "\n")
        f.write("\n---\n\n")
        for i, row in enumerate(results, 1):
            f.write(f"## {i}. Question\n\n{row['question']}\n\n")
            f.write("### Answer\n\n")
            f.write((row["answer"] or "(empty)") + "\n\n")
            f.write("### Sources\n\n")
            if row["sources"]:
                for s in row["sources"]:
                    src = s.get("source", "Unknown")
                    score = s.get("score")
                    url = s.get("url")
                    meta = f" (score: {score:.2f})" if isinstance(score, (int, float)) else ""
                    if url:
                        f.write(f"- {src}{meta} — {url}\n")
                    else:
                        f.write(f"- {src}{meta}\n")
            else:
                f.write("(none)\n")
            f.write("\n\n")

    print(f"Wrote: {jsonl_path}")
    print(f"Wrote: {md_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--in", dest="infile", default="scripts/questions.txt", help="Text file with one question per line")
    parser.add_argument("--out", dest="outdir", default="scripts/output", help="Output directory")
    parser.add_argument("--filesuffix", dest="suffix", default="", help="Optional suffix to append to output filenames for run labeling")
    args = parser.parse_args()

    questions = read_questions(Path(args.infile))
    out_dir = Path(args.outdir)

    results = []
    for q in questions:
        start = time.time()
        ans, src = ask(args.api, q)
        elapsed_ms = int((time.time() - start) * 1000)
        results.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "question": q,
            "answer": ans,
            "sources": src,
            "elapsed_ms": elapsed_ms,
        })
        print(f"✓ {elapsed_ms} ms | {q[:80]}")

    save_outputs(results, out_dir, args.suffix)


if __name__ == "__main__":
    main()


