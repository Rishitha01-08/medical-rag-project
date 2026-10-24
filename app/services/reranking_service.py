"""Deterministic lexical-overlap fallback reranker."""

from app.retrieval.bm25_retriever import tokenize


def rerank(question, documents, top_k=3):
    query_terms = set(tokenize(question))
    ranked = []
    for doc in documents:
        terms = set(tokenize(doc.get("content", "")))
        score = len(query_terms & terms) / max(1, len(query_terms))
        ranked.append({**doc, "rerank_score": score})
    ordered = sorted(ranked, key=lambda d: (-d["rerank_score"], d["chunk_id"]))[:top_k]
    return [{**item, "rank": rank} for rank, item in enumerate(ordered, 1)]
