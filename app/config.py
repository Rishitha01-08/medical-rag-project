"""Validated environment configuration. Secret values are never rendered."""

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be a boolean")
    return value.lower() in {"true", "1", "yes"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be a number") from None


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    mock_mode: bool = _bool("MOCK_MODE", True)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = _int("PORT", 8000)
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
    llm_model: str = os.getenv("LLM_MODEL", "mock-evidence-v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "deterministic-token-v1")
    vector_db_url: str = os.getenv("VECTOR_DB_URL", "")
    vector_collection: str = os.getenv("VECTOR_COLLECTION", "medical_docs")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    top_k_dense: int = _int("TOP_K_DENSE", 5)
    top_k_bm25: int = _int("TOP_K_BM25", 5)
    top_k_rerank: int = _int("TOP_K_RERANK", 3)
    min_relevance_score: float = _float("MIN_RELEVANCE_SCORE", 0.01)
    max_context_chars: int = _int("MAX_CONTEXT_CHARS", 6000)
    ingestion_api_key: str = os.getenv("INGESTION_API_KEY", "")
    debug_retrieval: bool = _bool("DEBUG_RETRIEVAL", False)
    chunk_size: int = _int("CHUNK_SIZE", 180)
    chunk_overlap: int = _int("CHUNK_OVERLAP", 30)
    rate_limit_requests: int = _int("RATE_LIMIT_REQUESTS", 60)
    rate_limit_window_seconds: int = _int("RATE_LIMIT_WINDOW_SECONDS", 60)

    def validate(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a standard logging level")
        if self.llm_provider not in {"mock", "openai", "gemini"}:
            raise ValueError("LLM_PROVIDER must be mock, openai, or gemini")
        if not self.mock_mode and self.llm_provider == "mock":
            raise ValueError("Set LLM_PROVIDER to openai or gemini when MOCK_MODE=false")
        if min(self.top_k_dense, self.top_k_bm25, self.top_k_rerank) < 1:
            raise ValueError("TOP_K settings must be positive")
        if not 0 <= self.min_relevance_score <= 1:
            raise ValueError("MIN_RELEVANCE_SCORE must be between 0 and 1")
        if self.max_context_chars < 1:
            raise ValueError("MAX_CONTEXT_CHARS must be positive")
        if self.chunk_size <= self.chunk_overlap or self.chunk_overlap < 0:
            raise ValueError("CHUNK_SIZE must be greater than non-negative CHUNK_OVERLAP")
        if not self.mock_mode and self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when MOCK_MODE=false and LLM_PROVIDER=openai"
            )
        if not self.mock_mode and self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when MOCK_MODE=false and LLM_PROVIDER=gemini"
            )


settings = Settings()
settings.validate()
