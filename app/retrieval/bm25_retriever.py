"""Small deterministic BM25 implementation for local educational corpora."""

import math
import re
from collections import Counter
from typing import Any

TOKEN = re.compile(r"[a-z0-9]+", re.I)


def tokenize(text):
    return [term.lower() for term in TOKEN.findall(text)]


def unique_documents(documents):
    unique: dict[str, dict[str, Any]] = {}
    for document in documents:
        unique.setdefault(document["chunk_id"], document)
    return list(unique.values())


class BM25Retriever:
    def __init__(self, documents, k1=1.5, b=0.75):
        self.documents = unique_documents(documents)
        self.k1, self.b = k1, b
        self.terms = [Counter(tokenize(d.get("content", ""))) for d in self.documents]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.average_length = sum(self.lengths) / max(1, len(self.lengths))
        self.df = Counter(term for counts in self.terms for term in counts)

    def search(self, query, top_k=5):
        query_terms = set(tokenize(query))
        ranked = []
        count = len(self.documents)
        for doc, terms, length in zip(self.documents, self.terms, self.lengths):
            score = 0.0
            for term in query_terms:
                frequency = terms[term]
                if not frequency:
                    continue
                idf = math.log(1 + (count - self.df[term] + 0.5) / (self.df[term] + 0.5))
                denom = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(1, self.average_length)
                )
                score += idf * frequency * (self.k1 + 1) / denom
            if score > 0:
                ranked.append({**doc, "score": score, "retrieval_source": "bm25"})
        ordered = sorted(ranked, key=lambda item: (-item["score"], item["chunk_id"]))[:top_k]
        return [{**item, "rank": rank} for rank, item in enumerate(ordered, 1)]
