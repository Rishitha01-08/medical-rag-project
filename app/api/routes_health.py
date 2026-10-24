from fastapi import APIRouter, HTTPException

from app.services.index_manifest import read_index_manifest
from app.services.lexical_index_service import keyword_index_count, keyword_index_ready
from app.services.vector_store_service import vector_store_count, vector_store_ready

router = APIRouter(tags=["health"])


@router.get(
    "/health", summary="Service health", description="Returns non-sensitive process health only."
)
def health():
    from app.config import settings

    return {
        "status": "ok",
        "mock_mode": settings.mock_mode,
        "provider": "mock" if settings.mock_mode else settings.llm_provider,
    }


@router.get(
    "/ready",
    summary="Readiness",
    description="Checks local corpus availability without exposing credentials.",
)
def ready():
    from app.config import settings

    try:
        qdrant_ready = vector_store_ready()
        lexical_ready = keyword_index_ready()
    except Exception:
        raise HTTPException(status_code=503, detail="Search indexes are unavailable.") from None
    if not qdrant_ready or not lexical_ready:
        manifest = read_index_manifest()
        vector_count = vector_store_count()
        keyword_count = keyword_index_count()
        raise HTTPException(
            status_code=503,
            detail={
                "message": "The complete vector and keyword indexes are not ready.",
                "vectors_indexed": vector_count,
                "keyword_chunks": keyword_count,
                "expected_chunks": manifest.get("expected_chunk_count") if manifest else None,
                "manifest_written": manifest is not None,
            },
        )
    manifest = read_index_manifest()
    return {
        "status": "ready",
        "vector_database": "qdrant",
        "keyword_index": "sqlite_fts5",
        "collection": settings.vector_collection,
        "indexed_chunks": manifest.get("expected_chunk_count") if manifest else None,
        "total_chunks": manifest.get("total_chunk_count") if manifest else None,
        "corpus_coverage": "complete" if manifest and manifest.get("corpus_complete", True) else "partial",
        "chunker_version": manifest.get("chunker_version") if manifest else None,
        "provider": "mock" if settings.mock_mode else settings.llm_provider,
    }
