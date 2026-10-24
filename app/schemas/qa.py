"""Question and answer payload schemas."""

from typing import Literal

from pydantic import Field

from app.schemas.common import StrictModel


class Question(StrictModel):
    question: str = Field(min_length=1, max_length=2000, examples=["What does hydration mean?"])
    retrieval_mode: str = Field(default="hybrid", pattern="^(dense|bm25|hybrid|hybrid_rerank)$")


class Citation(StrictModel):
    source_id: str
    title: str
    source: str | None = None
    source_url: str | None = None
    page_number: int | None = None
    section: str | None = None
    excerpt: str


class SafetyMetadata(StrictModel):
    category: Literal[
        "factual",
        "multi-part",
        "ambiguous",
        "safety-sensitive",
        "unsupported",
        "prompt-injection-attempt",
    ]
    emergency: bool
    abstained: bool
    citation_support: float


class RetrievalDiagnostic(StrictModel):
    chunk_id: str
    rank: int
    retrieval_source: str | None = None
    source_ranks: dict[str, int] = Field(default_factory=dict)
    score: float | None = None
    rerank_score: float | None = None


class ObservabilityMetadata(StrictModel):
    retrieval_count: int
    mode: str
    retrieval_latency_ms: float | None = None
    reranking_latency_ms: float | None = None
    generation_latency_ms: float | None = None
    total_latency_ms: float
    model: str | None = None
    token_usage: int | None = None
    estimated_cost: float | None = None
    retrieval_diagnostics: list[RetrievalDiagnostic] | None = None


class QAResponse(StrictModel):
    answer: str
    citations: list[Citation]
    disclaimer: str
    safety: SafetyMetadata
    observability: ObservabilityMetadata
