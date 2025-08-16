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


def fetch_masked_config(api_url: str) -> dict | None:
    """Fetch masked backend config for observability. Returns dict or None on error."""
    try:
        url = f"{api_url.rstrip('/')}/api/config"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        # Unwrap {"config": {...}} shape if the API wraps it
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            return data["config"]
        return data
    except Exception as exc:
        print(f"Warning: failed to fetch /api/config from {api_url}: {exc}")
        return None


def summarize_config(cfg: dict) -> dict:
    """Return a concise, masked summary suitable for printing or embedding in reports."""
    return {
        "OPENAI_API_KEY": "set" if cfg.get("OPENAI_API_KEY") and cfg["OPENAI_API_KEY"] != "not set" else "not set",
        "QDRANT_URL": "set" if cfg.get("QDRANT_URL") else "not set",
        "QDRANT_API_KEY": "set" if cfg.get("QDRANT_API_KEY") and cfg["QDRANT_API_KEY"] != "not set" else "not set",
        "TAVILY_API_KEY": "set" if cfg.get("TAVILY_API_KEY") and cfg["TAVILY_API_KEY"] != "not set" else "not set",
        "USE_POLICY_LOOP": cfg.get("USE_POLICY_LOOP"),
        "POLICY_STEP_CAP": cfg.get("POLICY_STEP_CAP"),
        "USE_WEB_AUGMENT": cfg.get("USE_WEB_AUGMENT"),
        "WEB_TOOL_FETCH_LIMIT": cfg.get("WEB_TOOL_FETCH_LIMIT"),
        "WEB_AUGMENT_MAX": cfg.get("WEB_AUGMENT_MAX"),
        "WEB_MIN_SCORE_GENERIC": cfg.get("WEB_MIN_SCORE_GENERIC"),
        "WEB_MIN_SCORE_RECALL": cfg.get("WEB_MIN_SCORE_RECALL"),
        "ALLOWED_ORIGINS": cfg.get("ALLOWED_ORIGINS"),
        "PORT": cfg.get("PORT"),
    }


def to_markdown_row(idx: int, q: str, ans: str, elapsed_ms: int) -> str:
    q_short = q.replace("|", r"\|")
    return f"| {idx} | {elapsed_ms} | {q_short} | {len(ans)} |"


def sanitize_suffix(suffix: str) -> str:
    """Make a human-provided suffix safe for filenames: keep letters, digits, _ and -; replace spaces with -."""
    s = suffix.strip().replace(" ", "-")
    return re.sub(r"[^A-Za-z0-9_\-]", "", s)


def save_outputs(
    results: list[dict],
    out_dir: Path,
    suffix: str | None = None,
    run_config_summary: dict | None = None,
    run_config_full: dict | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    suffix_clean = sanitize_suffix(suffix) if suffix else ""
    tag = f"{ts}" + (f"_{suffix_clean}" if suffix_clean else "")
    jsonl_path = out_dir / f"batch_results_{tag}.jsonl"
    md_path = out_dir / f"batch_results_{tag}.md"

    # JSONL
    with jsonl_path.open("w", encoding="utf-8") as f:
        if run_config_summary is not None:
            f.write(json.dumps({"type": "run_config", "summary": run_config_summary, "full": run_config_full}, ensure_ascii=False) + "\n")
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Markdown (summary + details)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# Batch Results ({datetime.utcnow().isoformat()}Z)\n\n")
        if run_config_summary is not None:
            f.write("## Run config (masked summary)\n\n")
            f.write("```json\n" + json.dumps(run_config_summary, indent=2, ensure_ascii=False) + "\n```\n\n")
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
    parser.add_argument("--print-config", dest="print_config", action="store_true", help="Fetch and print masked backend /api/config before running")
    args = parser.parse_args()

    run_cfg = None
    run_cfg_summary = None
    if args.print_config:
        cfg = fetch_masked_config(args.api)
        if cfg is not None:
            run_cfg = cfg
            run_cfg_summary = summarize_config(cfg)
            print("\nBackend /api/config (masked):")
            print(json.dumps(run_cfg_summary, indent=2, ensure_ascii=False))
            print("\nFull config blob (masked):")
            print(json.dumps(cfg, indent=2, ensure_ascii=False))
            print()

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

    save_outputs(results, out_dir, args.suffix, run_config_summary=run_cfg_summary, run_config_full=run_cfg)


if __name__ == "__main__":
    main()


