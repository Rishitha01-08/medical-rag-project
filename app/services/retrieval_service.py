"""End-to-end deterministic retrieval service."""

import json
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.retrieval.hybrid_retriever import retrieve
from app.services.reranking_service import rerank
from app.services.safety_service import contains_untrusted_instruction

LOCAL_STORE_PATH = Path("data/local/documents.jsonl")


def load_documents():
    docs = []
    for path in (
        LOCAL_STORE_PATH,
        Path("data/sample/sample_medical_corpus.jsonl"),
    ):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                docs.append(json.loads(line))
    unique: dict[str, dict[str, Any]] = {}
    for doc in docs:
        unique.setdefault(doc["chunk_id"], doc)
    return list(unique.values())


def search(question, mode="hybrid", documents=None):
    hits, _, _ = search_detailed(question, mode, documents)
    return hits


def search_detailed(question, mode="hybrid", documents=None):
    docs = documents if documents is not None else load_documents()
    started = time.perf_counter()
    retrieval_mode = "hybrid" if mode == "hybrid_rerank" else mode
    hits = retrieve(docs, question, retrieval_mode, settings.top_k_dense, settings.top_k_bm25)
    retrieval_ms = (time.perf_counter() - started) * 1000
    rerank_ms = 0.0
    if mode == "hybrid_rerank":
        rerank_started = time.perf_counter()
        hits = rerank(question, hits, settings.top_k_rerank)
        rerank_ms = (time.perf_counter() - rerank_started) * 1000
    hits = [
        hit
        for hit in hits
        if hit.get("score", hit.get("rerank_score", 0)) >= settings.min_relevance_score
    ]
    hits = [hit for hit in hits if not contains_untrusted_instruction(hit.get("content", ""))]
    return (
        hits[: settings.top_k_rerank if mode == "hybrid_rerank" else settings.top_k_dense],
        retrieval_ms,
        rerank_ms,
    )
