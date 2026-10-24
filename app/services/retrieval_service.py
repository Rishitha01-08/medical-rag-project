"""End-to-end deterministic retrieval service."""

import json
import time
from pathlib import Path
from typing import Any

from app.config import settings
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.hybrid_retriever import retrieve
from app.services.lexical_index_service import keyword_index_ready, search_keyword
from app.services.reranking_service import rerank
from app.services.safety_service import contains_untrusted_instruction
from app.services.vector_store_service import search_dense, vector_store_ready

LOCAL_STORE_PATH = Path("data/local/documents.jsonl")

# A deliberately small set of unambiguous spelling variants for topics present
# in the demo corpus. This helps conversational questions without attempting to
# autocorrect medical terminology or infer a diagnosis.
QUERY_ALIASES = {"slepp": "sleep", "sllep": "sleep", "handwashng": "handwashing"}


def normalize_query(question):
    return " ".join(QUERY_ALIASES.get(word.casefold(), word) for word in question.split())


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
    started = time.perf_counter()
    retrieval_question = normalize_query(question)
    if documents is not None:
        retrieval_mode = "hybrid" if mode == "hybrid_rerank" else mode
        hits = retrieve(
            documents, retrieval_question, retrieval_mode, settings.top_k_dense, settings.top_k_bm25
        )
    else:
        if mode not in {"dense", "bm25", "hybrid", "hybrid_rerank"}:
            raise ValueError("Unsupported retrieval mode")
        if vector_store_ready() and keyword_index_ready():
            if mode == "dense":
                hits = search_dense(retrieval_question, settings.top_k_dense)
            elif mode == "bm25":
                hits = search_keyword(retrieval_question, settings.top_k_bm25)
            else:
                dense_hits = search_dense(retrieval_question, settings.top_k_dense)
                keyword_hits = search_keyword(retrieval_question, settings.top_k_bm25)
                hits = reciprocal_rank_fusion({"dense": dense_hits, "bm25": keyword_hits})
        elif settings.app_env == "development":
            # Never silently answer from the tiny sample when a supplied corpus
            # exists but its complete indexes are not ready.
            supplied_corpus = any(Path("data/raw/hack-a-cure").glob("*.txt"))
            if supplied_corpus:
                raise RuntimeError(
                    "The supplied corpus is not fully indexed; check /ready and rebuild indexes."
                )
            hits = retrieve(load_documents(), retrieval_question, mode, settings.top_k_dense, settings.top_k_bm25)
        else:
            raise RuntimeError(
                "Search indexes are missing; run scripts/index_vector_store.py first."
            )
    retrieval_ms = (time.perf_counter() - started) * 1000
    rerank_ms = 0.0
    if mode == "hybrid_rerank":
        rerank_started = time.perf_counter()
        hits = rerank(retrieval_question, hits, settings.top_k_rerank)
        rerank_ms = (time.perf_counter() - rerank_started) * 1000
    if mode in {"dense", "bm25"} or documents is not None:
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
