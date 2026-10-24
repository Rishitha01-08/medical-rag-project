"""Score real application responses against retrieved evidence with RAGAS."""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from ragas.llms import llm_factory
from ragas.metrics.collections import ContextUtilization, Faithfulness

from app.config import settings
from app.services.lexical_index_service import keyword_index_ready
from app.services.qa_service import answer_question
from app.services.retrieval_service import search_detailed
from app.services.vector_store_service import vector_store_ready

load_dotenv()


def load_cases(path=Path("evaluation/questions.jsonl")):
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


async def evaluate_cases(cases, model_name):
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set GOOGLE_API_KEY or GEMINI_API_KEY in your local environment before RAGAS evaluation."
        )
    client = genai.Client(api_key=api_key)
    judge = llm_factory(model_name, provider="google", client=client)
    metrics = [Faithfulness(llm=judge), ContextUtilization(llm=judge)]
    rows = []
    for case in cases:
        question = case["question"]
        hits, _, _ = search_detailed(question, "hybrid")
        response = answer_question(question, "hybrid", retrieved_hits=hits)
        contexts = [hit["content"] for hit in hits]
        result = {
            "id": case["id"],
            "question": question,
            "answer": response["answer"],
            "retrieved_chunk_ids": [hit["chunk_id"] for hit in hits],
            "scores": {},
        }
        if not contexts:
            result["scores"] = {"faithfulness": None, "context_utilization": None}
            result["note"] = "Skipped judge metrics because retrieval returned no evidence."
        else:
            for metric in metrics:
                score = await metric.ascore(
                    user_input=question,
                    response=response["answer"],
                    retrieved_contexts=contexts,
                )
                result["scores"][metric.name] = float(score.value)
        rows.append(result)
    return rows


def main():
    if not vector_store_ready() or not keyword_index_ready():
        raise SystemExit(
            "Build both corpus indexes first: run scripts/ingest_text_corpus.py and "
            "scripts/index_vector_store.py."
        )
    model = os.getenv("RAGAS_MODEL", "gemini-2.0-flash")
    rows = asyncio.run(evaluate_cases(load_cases(), model))
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "evaluation_model": model,
        "application_mode": "mock" if settings.mock_mode else settings.llm_provider,
        "case_count": len(rows),
        "results": rows,
        "limitations": [
            "RAGAS scores are LLM judge estimates and depend on the evaluator model.",
            "This small, partly synthetic question set is not a clinical benchmark.",
            "Human review remains necessary; this report is not evidence of medical safety or correctness.",
        ],
    }
    output = Path("evaluation/reports/ragas-evaluation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote RAGAS judge report: {output}")


if __name__ == "__main__":
    main()
