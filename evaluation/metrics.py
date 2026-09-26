"""Deterministic ranking and response metrics; faithfulness is only a proxy."""

import math


def ranking_metrics(results, expected, k=5):
    ids = [row["chunk_id"] for row in results[:k]]
    relevant = set(expected)
    if not relevant:
        return {"recall_at_k": None, "precision_at_k": None, "mrr": None, "ndcg": None}
    hits = [i for i, chunk_id in enumerate(ids, 1) if chunk_id in relevant]
    precision = len(hits) / k if k else 0.0
    recall = len(hits) / len(relevant)
    reciprocal_rank = 1 / hits[0] if hits else 0.0
    dcg = sum(1 / math.log2(rank + 1) for rank in hits)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(relevant), k) + 1))
    return {
        "recall_at_k": recall,
        "precision_at_k": precision,
        "mrr": reciprocal_rank,
        "ndcg": dcg / ideal if ideal else 0.0,
    }


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct * len(ordered)) - 1)]
