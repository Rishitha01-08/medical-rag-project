"""Safe educational question-answering orchestration."""

import time

from app.config import settings
from app.observability.metrics import elapsed_ms
from app.services.generation_service import get_provider
from app.services.grounding_service import citation_support, citations_for
from app.services.retrieval_service import search_detailed
from app.services.safety_service import EMERGENCY, SENSITIVE, classify

DISCLAIMER = "Educational information only; not for diagnosis, treatment, or emergencies. Consult a qualified health professional."
UNSUPPORTED = "I could not find sufficient supporting evidence in the available educational corpus to answer this question."


def answer_question(question, mode="hybrid"):
    started = time.perf_counter()
    if EMERGENCY.search(question):
        return {
            "answer": "If this may be an emergency, contact your local emergency services now or seek immediate help from a qualified medical professional.",
            "citations": [],
            "disclaimer": DISCLAIMER,
            "safety": {
                "category": "safety-sensitive",
                "emergency": True,
                "abstained": True,
                "citation_support": 0.0,
            },
            "observability": {
                "retrieval_count": 0,
                "mode": mode,
                "total_latency_ms": elapsed_ms(started),
            },
        }
    if SENSITIVE.search(question):
        return {
            "answer": "I can provide general educational information, but cannot diagnose, recommend medicines, calculate doses, or create a treatment plan. Please consult a qualified health professional.",
            "citations": [],
            "disclaimer": DISCLAIMER,
            "safety": {
                "category": "safety-sensitive",
                "emergency": False,
                "abstained": True,
                "citation_support": 0.0,
            },
            "observability": {
                "retrieval_count": 0,
                "mode": mode,
                "total_latency_ms": elapsed_ms(started),
            },
        }
    if classify(question) == "prompt-injection-attempt":
        return {
            "answer": UNSUPPORTED,
            "citations": [],
            "disclaimer": DISCLAIMER,
            "safety": {
                "category": "prompt-injection-attempt",
                "emergency": False,
                "abstained": True,
                "citation_support": 0.0,
            },
            "observability": {
                "retrieval_count": 0,
                "mode": mode,
                "total_latency_ms": elapsed_ms(started),
            },
        }
    hits, retrieval_ms, reranking_ms = search_detailed(question, mode)
    remaining_context = settings.max_context_chars
    bounded_hits = []
    for hit in hits:
        if remaining_context <= 0:
            break
        bounded = dict(hit)
        bounded["content"] = hit.get("content", "")[:remaining_context]
        remaining_context -= len(bounded["content"])
        bounded_hits.append(bounded)
    hits = bounded_hits
    retrieval_ms = round(retrieval_ms, 3)
    reranking_ms = round(reranking_ms, 3)
    generation_started = time.perf_counter()
    provider, model_name = get_provider()
    generated = provider.generate(question, hits)
    generation_ms = round((time.perf_counter() - generation_started) * 1000, 3)
    support = (
        citation_support([claim.source_ids for claim in generated.claims], hits)
        if generated.claims
        else 0.0
    )
    abstained = (
        not hits or support < 1.0 or any(c.support_status != "supported" for c in generated.claims)
    )
    answer = UNSUPPORTED if abstained else generated.answer
    citations = citations_for(hits) if not abstained else []
    category = classify(question, evidence_available=bool(hits))
    observability = {
        "retrieval_count": len(hits),
        "mode": mode,
        "retrieval_latency_ms": retrieval_ms,
        "reranking_latency_ms": reranking_ms,
        "generation_latency_ms": generation_ms,
        "total_latency_ms": elapsed_ms(started),
        "model": model_name,
        "token_usage": None,
        "estimated_cost": None,
    }
    if settings.debug_retrieval and settings.app_env == "development":
        observability["retrieval_diagnostics"] = [
            {
                "chunk_id": hit["chunk_id"],
                "rank": hit["rank"],
                "retrieval_source": hit.get("retrieval_source"),
                "source_ranks": hit.get("source_ranks", {}),
                "score": hit.get("score"),
                "rerank_score": hit.get("rerank_score"),
            }
            for hit in hits
        ]
    return {
        "answer": answer,
        "citations": citations,
        "disclaimer": DISCLAIMER,
        "safety": {
            "category": category,
            "emergency": False,
            "abstained": abstained,
            "citation_support": support,
        },
        "observability": observability,
    }
