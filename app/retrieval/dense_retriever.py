"""Deterministic dependency-free dense-retriever interface fallback.

This mock-mode fallback uses token-vector cosine similarity; it does not claim to
produce semantic embeddings.
"""

import math
from collections import Counter

from app.retrieval.bm25_retriever import tokenize, unique_documents


class DenseRetriever:
    def __init__(self, documents):
        self.documents = unique_documents(documents)

    @staticmethod
    def _vector(text):
        return Counter(tokenize(text))

    def search(self, query, top_k=5):
        q = self._vector(query)
        ranked = []
        for doc in self.documents:
            vector = self._vector(doc.get("content", ""))
            dot = sum(q[t] * vector[t] for t in q)
            denom = math.sqrt(sum(v * v for v in q.values()) * sum(v * v for v in vector.values()))
            score = dot / denom if denom else 0.0
            if score:
                ranked.append({**doc, "score": score, "retrieval_source": "dense_mock"})
        ordered = sorted(ranked, key=lambda item: (-item["score"], item["chunk_id"]))[:top_k]
        return [{**item, "rank": rank} for rank, item in enumerate(ordered, 1)]
