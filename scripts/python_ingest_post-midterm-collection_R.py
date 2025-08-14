#!/usr/bin/env python3
"""
Enhanced ingestion script with structure-aware + semantic chunking, page anchors,
stable IDs, richer metadata, and fast filtered cleanup for Qdrant.

Usage examples:
  # Single strategy
  python ingest_enhanced.py InterNACHI --strategy heading_semantic_pack --suffix v1

  # Compare a few
  python ingest_enhanced.py InterNACHI --compare-subset heading_semantic_pack recursive token --suffix sweep1

  # List experiments
  python ingest_enhanced.py --list
"""

import os
import re
import sys
import uuid
import json
import math
import time
import hashlib
import random
import argparse
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

# Determinism helpers (for consistent evals)
import numpy as np
random.seed(42); np.random.seed(42)

from dotenv import load_dotenv

# LangChain imports
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter,
)
# Optional helpers
try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter
except Exception:
    MarkdownHeaderTextSplitter = None

try:
    # Semantic boundary detector (optional)
    from langchain_experimental.text_splitter import SemanticChunker
except Exception:
    SemanticChunker = None

# OpenAI embeddings (for both index & optional semantic chunking)
from langchain_openai import OpenAIEmbeddings

# PDF loader
from langchain_community.document_loaders import PyMuPDFLoader

# Token counting
try:
    import tiktoken
except Exception:
    tiktoken = None

# Qdrant direct client
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# -------------------------
# Configuration
# -------------------------
COLLECTION_NAME = 'post_midterm_R'
EMBEDDING_MODEL = 'text-embedding-3-small'  # 1536 dims
EMBED_DIM = 1536
DEFAULT_MODEL_FOR_TOKENS = "cl100k_base"    # for tiktoken counting (works for GPT-4/4o families)

# Documents map (adjust paths to your repo)
DOCUMENTS = {
    "InterNACHI": {
        "path": "../docs/data/InterNACHI.pdf",
        "source": "InterNACHI Standards of Practice",
        "category": "Standards",
    },
    "ASHI": {
        "path": "../docs/data/ASHI standards_updated3-4-2015.pdf",
        "source": "ASHI Standards of Practice",
        "category": "Standards",
    },
    "NCHILB": {
        "path": "../docs/data/NCHILB NORTH CAROLINA HOME INSPECTOR LICENSURE BOARD (1).pdf",
        "source": "NC Home Inspector Licensure Board",
        "category": "Regulations",
    },
    "NC_Codes": {
        "path": "../docs/data/2024_nc_collection_no_footer (1).pdf",
        "source": "NC Building Codes 2024",
        "category": "Building Codes",
    },
}

# -------------------------
# Strategies and presets
# -------------------------
class ChunkingStrategy(Enum):
    RECURSIVE = "recursive"
    CHARACTER = "character"
    TOKEN = "token"
    PARAGRAPH = "paragraph"
    HEADING_SEMANTIC_PACK = "heading_semantic_pack"  # structure→(semantic)→token-pack

STRATEGY_CONFIGS: Dict[ChunkingStrategy, Dict[str, Any]] = {
    ChunkingStrategy.RECURSIVE: {
        "chunk_size": 1000,      # characters
        "chunk_overlap": 200,
        "description": "Recursive splitting with hierarchical separators"
    },
    ChunkingStrategy.CHARACTER: {
        "chunk_size": 1000,      # characters
        "chunk_overlap": 100,
        "description": "Simple character-based splitting"
    },
    ChunkingStrategy.TOKEN: {
        "chunk_size": 512,       # tokens
        "chunk_overlap": 64,
        "description": "Token-based splitting"
    },
    ChunkingStrategy.PARAGRAPH: {
        "chunk_size": 2000,      # characters
        "chunk_overlap": 200,
        "description": "Paragraph-aware recursive splitting"
    },
    ChunkingStrategy.HEADING_SEMANTIC_PACK: {
        "chunk_size": 600,       # target tokens after packing
        "chunk_overlap": 80,     # tokens (~13%)
        "description": "Split by headings, optionally refine via semantic boundaries, pack to token window"
    },
}

# -------------------------
# Utilities
# -------------------------
def make_point_id(doc_source: str,
                  experiment_label: str,
                  page_start: int,
                  page_end: int,
                  local_idx: int,
                  content: str) -> Tuple[str, str]:
    """Create a stable point ID using position + full-content hash.

    Returns (primary_id, dedup_hash).
    - primary_id ensures identical text at different positions does not collide
    - dedup_hash allows optional dedup analytics across runs
    """
    content_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    loc = f"{page_start}-{page_end}-{local_idx}"
    raw = f"{doc_source}|{experiment_label}|{loc}|{content_sha}"
    # Qdrant accepts only integer or UUID IDs; use deterministic UUIDv5
    primary_uuid = uuid.uuid5(uuid.NAMESPACE_URL, raw)
    return str(primary_uuid), content_sha

def get_token_encoder():
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding(DEFAULT_MODEL_FOR_TOKENS)
    except Exception:
        # Fallback to a widely available encoding
        return tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    enc = get_token_encoder()
    if enc is None:
        # rough fallback
        return math.ceil(len(text) / 4)
    return len(enc.encode(text))

def _clean_page_text(t: str) -> str:
    # remove common header/footer-only lines
    lines = [
        ln for ln in t.splitlines()
        if not re.match(r'^\s*(Page\s+\d+|\d+\s*/\s*\d+)\s*$', ln)
    ]
    t = "\n".join(lines)
    # de-hyphenate line-break hyphens
    t = re.sub(r'(\w)-\n(\w)', r'\1\2', t)
    # normalize whitespace
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t

def extract_pages_with_meta(file_path: str) -> List[Document]:
    """Load PDF as one Document per page with cleaned text and page anchors."""
    loader = PyMuPDFLoader(file_path)
    pages = loader.load()
    docs: List[Document] = []
    for p in pages:
        txt = _clean_page_text(p.page_content or "")
        meta = dict(p.metadata or {})
        # normalize page index (PyMuPDFLoader sets 'page' or 'page_number')
        page_no = meta.get("page", meta.get("page_number"))
        meta.update({
            "page": page_no,
            "file_path": file_path,
        })
        docs.append(Document(page_content=txt, metadata=meta))
    return docs

def maybe_semantic_chunker(embeddings: OpenAIEmbeddings, threshold_type: str = "percentile", threshold: int = 95):
    """Return a SemanticChunker if available, else None."""
    if SemanticChunker is None:
        return None
    try:
        return SemanticChunker(
            embeddings,
            breakpoint_threshold_type=threshold_type,
            threshold=threshold
        )
    except Exception:
        return None

def pack_to_tokens(texts: List[str], target_tokens=600, overlap=80, model_name_for_splitter: str = "gpt-4o-mini") -> List[str]:
    """Pack arbitrary texts into token windows with overlap."""
    splitter = TokenTextSplitter(
        chunk_size=target_tokens,
        chunk_overlap=overlap,
        model_name=model_name_for_splitter,
    )
    packed: List[str] = []
    for t in texts:
        if not t:
            continue
        parts = splitter.split_text(t)
        packed.extend(parts)
    return packed

def detect_headings_paragraphs(page_docs: List[Document]) -> List[Tuple[str, Optional[int], Optional[int], Optional[str]]]:
    """
    Naive heading-aware sectioning:
      - Start new section on ALL-CAPS or numbered headings like "1.", "1.1", "1.1.1 Title"
      - Return list of (section_text, page_start, page_end, section_heading)
    """
    heading_rx = re.compile(r'^[A-Z][A-Z \d\-\(\)\.,:/]{4,}$|^\d+(\.\d+){0,3}\s+.+$')
    sections: List[Tuple[str, Optional[int], Optional[int], Optional[str]]] = []
    buf: List[str] = []
    section_heading: Optional[str] = None
    start_page: Optional[int] = None
    last_page: Optional[int] = None

    def flush():
        if buf:
            sections.append(("\n\n".join(buf).strip(), start_page, last_page, section_heading))

    for d in page_docs:
        last_page = d.metadata.get("page")
        # split page into paragraphs
        paras = [p for p in (d.page_content or "").split("\n\n") if p.strip()]
        for para in paras:
            if heading_rx.match(para.strip()):
                # new section
                if buf:
                    flush()
                    buf = []
                section_heading = para.strip()
                start_page = d.metadata.get("page")
            buf.append(para)

    # final flush
    if buf:
        flush()
    return sections

# -------------------------
# Pipeline
# -------------------------
class ChunkingPipeline:
    def __init__(self):
        self.collection_name = COLLECTION_NAME
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.qdrant = QdrantClient(
            url=os.environ.get("QDRANT_URL"),
            api_key=os.environ.get("QDRANT_API_KEY"),
        )

    def ensure_collection_exists(self):
        try:
            info = self.qdrant.get_collection(self.collection_name)
            print(f"✅ Collection exists: {self.collection_name} ({info.points_count} points)")
        except Exception:
            print(f"📋 Creating collection: {self.collection_name}")
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
            )
            print(f"✅ Created collection: {self.collection_name}")

    def generate_experiment_label(self, strategy: ChunkingStrategy, custom_suffix: Optional[str] = None) -> str:
        cfg = STRATEGY_CONFIGS[strategy]
        base = f"{strategy.value}_{cfg['chunk_size']}_{cfg['chunk_overlap']}"
        if custom_suffix:
            base += f"_{custom_suffix}"
        return base

    def create_text_splitter(self, strategy: ChunkingStrategy):
        cfg = STRATEGY_CONFIGS[strategy]
        size = cfg["chunk_size"]
        overlap = cfg["chunk_overlap"]

        if strategy == ChunkingStrategy.RECURSIVE:
            return RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", ". ", ".", " ", ""],
            )

        if strategy == ChunkingStrategy.CHARACTER:
            return CharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                separator="",
                length_function=len,
            )

        if strategy == ChunkingStrategy.TOKEN:
            return TokenTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                model_name="gpt-4o-mini",  # tiktoken model id
            )

        if strategy == ChunkingStrategy.PARAGRAPH:
            return RecursiveCharacterTextSplitter(
                chunk_size=size,
                chunk_overlap=overlap,
                length_function=len,
                is_separator_regex=False,
                separators=["\n\n", "\n", ". ", ".", " ", ""],
                keep_separator=True,
            )

        if strategy == ChunkingStrategy.HEADING_SEMANTIC_PACK:
            return None  # handled custom in ingest_document

        raise ValueError(f"Unknown strategy: {strategy}")

    def cleanup_experiment(self, source_name: str, experiment_label: str) -> int:
        """Fast delete via filter; falls back to scroll if server doesn’t support it."""
        print(f"🧹 Cleanup: source='{source_name}', experiment='{experiment_label}'")
        flt = Filter(
            must=[
                FieldCondition(key="source", match=MatchValue(value=source_name)),
                FieldCondition(key="experiment_label", match=MatchValue(value=experiment_label)),
            ]
        )
        try:
            res = self.qdrant.delete(collection_name=self.collection_name, points_selector=flt, wait=True)
            print("✅ Cleanup via filter complete")
            return 0  # Qdrant doesn't return deleted count; 0 means we didn't track it
        except Exception as e:
            print(f"⚠️ Filter delete failed ({e}); falling back to scroll...")
            # Fallback scroll+delete-by-ids
            deleted = 0
            offset = None
            while True:
                batch, offset = self.qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    offset=offset,
                    with_payload=True
                )
                if not batch:
                    break
                ids = [
                    pt.id for pt in batch
                    if (pt.payload or {}).get("source") == source_name
                    and (pt.payload or {}).get("experiment_label") == experiment_label
                ]
                if ids:
                    self.qdrant.delete(collection_name=self.collection_name, points_selector=ids, wait=True)
                    deleted += len(ids)
            print(f"✅ Cleanup via scroll complete, deleted ~{deleted}")
            return deleted

    def list_experiments(self, source_name: Optional[str] = None) -> Dict[str, int]:
        experiments: Dict[str, int] = {}
        offset = None
        print(f"📊 Scanning experiments in {self.collection_name}...")
        while True:
            batch, offset = self.qdrant.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["source", "experiment_label"]
            )
            if not batch:
                break
            for pt in batch:
                src = (pt.payload or {}).get("source", "unknown")
                exp = (pt.payload or {}).get("experiment_label", "unknown")
                if source_name and src != source_name:
                    continue
                key = f"{src} | {exp}"
                experiments[key] = experiments.get(key, 0) + 1
            if not offset:
                break
        return experiments

    # -------------------------
    # INGEST
    # -------------------------
    def ingest_document(
        self,
        doc_key: str,
        strategy: ChunkingStrategy,
        experiment_suffix: Optional[str] = None,
        cleanup: bool = True
    ) -> Dict[str, Any]:
        if doc_key not in DOCUMENTS:
            raise ValueError(f"Unknown document: {doc_key}")

        doc_info = DOCUMENTS[doc_key]
        cfg = STRATEGY_CONFIGS[strategy]
        experiment_label = self.generate_experiment_label(strategy, experiment_suffix)

        print(f"\n📄 Processing: {doc_key}")
        print(f"   Strategy: {strategy.value} - {cfg['description']}")
        print(f"   Experiment: {experiment_label}")
        print(f"   Source: {doc_info['source']}")

        file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), doc_info["path"]))
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"   File: {file_path} ({size_mb:.1f} MB)")

        # Ensure collection
        self.ensure_collection_exists()

        # Cleanup for this (source, experiment)
        if cleanup:
            self.cleanup_experiment(doc_info["source"], experiment_label)

        # Page-aware extract
        print("📝 Extracting pages with cleanup...")
        page_docs = extract_pages_with_meta(file_path)
        print(f"   Pages: {len(page_docs)}")

        # Build chunks
        print("✂️  Building chunks...")
        if strategy == ChunkingStrategy.HEADING_SEMANTIC_PACK:
            chunks, meta = self._build_heading_semantic_pack(page_docs, cfg)
        else:
            # Use LC splitters over documents to retain page metadata
            splitter = self.create_text_splitter(strategy)
            doc_chunks = splitter.split_documents(page_docs)  # type: ignore
            chunks = [d.page_content for d in doc_chunks]
            meta = []
            for d in doc_chunks:
                m = dict(d.metadata or {})
                m.setdefault("page_start", m.get("page"))  # best effort
                m.setdefault("page_end", m.get("page"))
                m.setdefault("section_heading", None)
                meta.append(m)

        # Stats
        chunk_sizes = [len(c) for c in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
        min_size = min(chunk_sizes) if chunk_sizes else 0
        max_size = max(chunk_sizes) if chunk_sizes else 0
        print(f"   Created: {len(chunks)} chunks | avg={avg_size:.0f} chars, min={min_size}, max={max_size}")

        # Embeddings + upload
        print("🔄 Creating embeddings and uploading...")
        batch_size = 25
        total_uploaded = 0
        total = len(chunks)
        for i in range(0, total, batch_size):
            batch_chunks = chunks[i:i+batch_size]
            batch_meta = meta[i:i+batch_size]
            emb = self.embeddings.embed_documents(batch_chunks)

            points: List[PointStruct] = []
            for j, (content, vec) in enumerate(zip(batch_chunks, emb)):
                idx = i + j
                m = batch_meta[j] if j < len(batch_meta) else {}
                tok_count = count_tokens(content)

                payload = {
                    "content": content,
                    "source": doc_info["source"],
                    "document_name": doc_info["source"],
                    "category": doc_info["category"],
                    "chunk_index": idx,
                    "total_chunks": total,
                    "file_name": os.path.basename(file_path),
                    "experiment_label": experiment_label,
                    "chunking_strategy": strategy.value,
                    "chunking_params": { "chunk_size": cfg["chunk_size"], "chunk_overlap": cfg["chunk_overlap"] },
                    "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
                    "token_count": tok_count,
                    # page + section metadata
                    "page_start": m.get("page_start"),
                    "page_end": m.get("page_end"),
                    "section_heading": m.get("section_heading"),
                }

                pstart = m.get("page_start", -1)
                pend = m.get("page_end", -1)
                pid, dedup_hash = make_point_id(
                    doc_info["source"],
                    experiment_label,
                    pstart,
                    pend,
                    idx,
                    content,
                )
                payload["dedup_hash"] = dedup_hash
                points.append(PointStruct(id=pid, vector=vec, payload=payload))

            self.qdrant.upsert(collection_name=self.collection_name, points=points, wait=True)
            total_uploaded += len(points)
            print(f"   📦 Uploaded {total_uploaded}/{total}")

        info = self.qdrant.get_collection(self.collection_name)
        print(f"🎉 Completed: {total_uploaded} chunks ingested (collection now has {info.points_count} points)")
        return {
            "strategy": strategy.value,
            "experiment_label": experiment_label,
            "chunks_created": len(chunks),
            "chunks_uploaded": total_uploaded,
            "avg_chunk_size_chars": avg_size,
            "min_chunk_size_chars": min_size,
            "max_chunk_size_chars": max_size,
            "total_collection_points": info.points_count
        }

    # ---- custom builder for HEADING → (semantic) → PACK
    def _build_heading_semantic_pack(self, page_docs: List[Document], cfg: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
        sections = detect_headings_paragraphs(page_docs)  # (text, page_start, page_end, heading)
        if not sections:
            # fallback: treat whole doc as one section
            whole = "\n\n".join(d.page_content for d in page_docs)
            sections = [(whole, page_docs[0].metadata.get("page"), page_docs[-1].metadata.get("page"), None)]

        # Optional semantic boundary refinement per section
        sem = maybe_semantic_chunker(self.embeddings)
        refined_texts: List[Tuple[str, Optional[int], Optional[int], Optional[str]]] = []
        for (text, pstart, pend, heading) in sections:
            if sem:
                try:
                    parts = sem.split_text(text)
                    for p in parts:
                        refined_texts.append((p, pstart, pend, heading))
                except Exception:
                    refined_texts.append((text, pstart, pend, heading))
            else:
                refined_texts.append((text, pstart, pend, heading))

        # Pack to target token window with overlap
        target_tokens = cfg["chunk_size"]
        overlap = cfg["chunk_overlap"]

        # We pack per refined segment to preserve local coherence
        final_chunks: List[str] = []
        final_meta: List[Dict[str, Any]] = []
        for (text, pstart, pend, heading) in refined_texts:
            packed = pack_to_tokens([text], target_tokens=target_tokens, overlap=overlap, model_name_for_splitter="gpt-4o-mini")
            for p in packed:
                final_chunks.append(p)
                final_meta.append({
                    "page_start": pstart,
                    "page_end": pend,
                    "section_heading": heading
                })
        return final_chunks, final_meta

# -------------------------
# Comparison helpers
# -------------------------
def compare_strategies(doc_key: str, strategies: List[ChunkingStrategy], suffix: Optional[str] = None):
    pipe = ChunkingPipeline()
    results = []
    print(f"\n🔬 COMPARING STRATEGIES FOR: {doc_key}")
    print("=" * 72)
    for s in strategies:
        try:
            r = pipe.ingest_document(doc_key, s, experiment_suffix=suffix, cleanup=True)
            results.append(r)
        except Exception as e:
            print(f"❌ {s.value}: {e}")
            results.append({"strategy": s.value, "error": str(e)})

    print("\n📊 COMPARISON RESULTS")
    print("=" * 72)
    print(f"{'Strategy':<24} {'Label':<36} {'Chunks':>8} {'Avg chars':>10}")
    print("-"*72)
    for r in results:
        if "error" in r:
            print(f"{r['strategy']:<24} {'ERROR':<36} {'-':>8} {'-':>10}")
        else:
            print(f"{r['strategy']:<24} {r['experiment_label']:<36} {r['chunks_created']:>8} {int(r['avg_chunk_size_chars']):>10}")
    print("\n💡 Query with a filter like:")
    print('   {"must":[{"key":"experiment_label","match":{"value":"<label>"}}]}')

def list_all_experiments():
    pipe = ChunkingPipeline()
    exps = pipe.list_experiments()
    if not exps:
        print("📭 No experiments found")
        return
    print(f"\n📊 EXPERIMENTS IN COLLECTION: {COLLECTION_NAME}")
    print("=" * 72)
    print(f"{'Source':<40} {'Experiment Label':<24} {'Chunks':>8}")
    print("-"*72)
    for key, cnt in sorted(exps.items()):
        src, lbl = (key.split(" | ")+[""])[:2]
        if len(src) > 38:
            src = src[:35] + "..."
        print(f"{src:<40} {lbl:<24} {cnt:>8}")

# -------------------------
# CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Ingest documents with upgraded chunking strategies")
    parser.add_argument("document", nargs="?", choices=list(DOCUMENTS.keys()), help="Document to ingest")
    parser.add_argument("--strategy", type=str, choices=[s.value for s in ChunkingStrategy], help="Chunking strategy")
    parser.add_argument("--compare", action="store_true", help="Compare ALL strategies")
    parser.add_argument("--compare-subset", nargs="+", choices=[s.value for s in ChunkingStrategy], help="Compare selected strategies")
    parser.add_argument("--suffix", type=str, help="Custom suffix for experiment label (e.g., 'v2')")
    parser.add_argument("--no-cleanup", action="store_true", help="Do not cleanup existing chunks for this experiment")
    parser.add_argument("--list", action="store_true", help="List all experiments in the collection")

    args = parser.parse_args()
    try:
        if args.list:
            list_all_experiments()
            return

        if not args.document and not args.list:
            parser.error("Document is required unless using --list")

        if args.compare:
            strategies = list(ChunkingStrategy)
            compare_strategies(args.document, strategies, args.suffix)
            return

        if args.compare_subset:
            strategies = [ChunkingStrategy(s) for s in args.compare_subset]
            compare_strategies(args.document, strategies, args.suffix)
            return

        # Single run
        pipeline = ChunkingPipeline()
        if args.strategy:
            strat = ChunkingStrategy(args.strategy)
        else:
            strat = ChunkingStrategy.RECURSIVE  # default baseline

        res = pipeline.ingest_document(
            args.document,
            strat,
            experiment_suffix=args.suffix,
            cleanup=not args.no_cleanup
        )

        print("\n✅ SUCCESS")
        for k, v in res.items():
            if k != "chunking_params":
                print(f"   {k}: {v}")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
