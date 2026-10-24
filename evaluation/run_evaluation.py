"""Run reproducible retrieval ablations over synthetic examples."""

import json
from pathlib import Path
from statistics import mean

from app.config import settings
from app.services.qa_service import answer_question
from app.services.retrieval_service import load_documents, search
from evaluation.metrics import percentile, ranking_metrics

MODES = ("dense", "bm25", "hybrid", "hybrid_rerank")


def main():
    corpus = load_documents()
    cases = [
        json.loads(line)
        for line in Path("evaluation/questions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = {
        "configuration": {
            "mock_mode": settings.mock_mode,
            "llm_provider": "mock" if settings.mock_mode else settings.llm_provider,
            "retrieval_modes": list(MODES),
            "top_k_dense": settings.top_k_dense,
            "top_k_bm25": settings.top_k_bm25,
            "top_k_rerank": settings.top_k_rerank,
            "min_relevance_score": settings.min_relevance_score,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
        },
        "corpus_size": len(corpus),
        "evaluation_size": len(cases),
        "results": {},
        "failure_examples": {},
        "known_limitations": [
            "Synthetic examples only; metrics are deterministic retrieval proxies, not clinical or model-quality measurements.",
            "Token-vector dense mode is a local fallback, not a pretrained embedding model.",
            "Latency is process-local and is not a production benchmark.",
        ],
    }
    for mode in MODES:
        rows, latency, support, abstention_ok = [], [], [], []
        failures = []
        for case in cases:
            hits = search(case["question"], mode)
            rows.append(ranking_metrics(hits, case["expected_chunk_ids"]))
            retrieved_ids = [item["chunk_id"] for item in hits]
            if case["expected_chunk_ids"] and not set(retrieved_ids) & set(
                case["expected_chunk_ids"]
            ):
                failures.append(
                    {
                        "question_id": case["id"],
                        "expected_chunk_ids": case["expected_chunk_ids"],
                        "retrieved_chunk_ids": retrieved_ids,
                    }
                )
            answer = answer_question(case["question"], mode)
            latency.append(answer["observability"]["total_latency_ms"])
            support.append(answer["safety"]["citation_support"])
            abstention_ok.append(answer["safety"]["abstained"] == case["should_abstain"])
        rank_scores = {
            metric: [item[metric] for item in rows if item[metric] is not None]
            for metric in rows[0]
        }
        report["results"][mode] = {
            metric: round(mean(values), 4) if values else None
            for metric, values in rank_scores.items()
        }
        report["results"][mode].update(
            {
                "citation_support_rate_proxy": round(mean(support), 4),
                "groundedness_proxy": round(mean(support), 4),
                "abstention_accuracy": round(mean(abstention_ok), 4),
                "p50_latency_ms": percentile(latency, 0.50),
                "p95_latency_ms": percentile(latency, 0.95),
                "error_rate": 0.0,
            }
        )
        report["failure_examples"][mode] = failures
    output = Path("evaluation/reports/mock-evaluation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote deterministic proxy report: {output}")


if __name__ == "__main__":
    main()
