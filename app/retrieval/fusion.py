"""Rank fusion helpers."""

from collections import defaultdict
from typing import Any


def reciprocal_rank_fusion(result_lists, k: int = 60):
    scores: defaultdict[str, float] = defaultdict(float)
    docs: dict[str, dict[str, Any]] = {}
    ranks: dict[str, dict[str, int]] = {}
    for source, results in result_lists.items():
        for rank, doc in enumerate(results, 1):
            key = doc["chunk_id"]
            scores[key] += 1.0 / (k + rank)
            docs.setdefault(key, dict(doc))
            ranks.setdefault(key, {})[source] = rank
    fused = []
    for key, score in scores.items():
        fused.append(
            {**docs[key], "score": score, "retrieval_source": "hybrid", "source_ranks": ranks[key]}
        )
    ordered = sorted(fused, key=lambda d: (-d["score"], d["chunk_id"]))
    return [{**item, "rank": rank} for rank, item in enumerate(ordered, 1)]
