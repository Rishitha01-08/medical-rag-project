from fastapi import APIRouter

from app.services.retrieval_service import load_documents

router = APIRouter(tags=["health"])


@router.get(
    "/health", summary="Service health", description="Returns non-sensitive process health only."
)
def health():
    from app.config import settings

    return {"status": "ok", "mock_mode": settings.mock_mode}


@router.get(
    "/ready",
    summary="Readiness",
    description="Checks local corpus availability without exposing credentials.",
)
def ready():
    from app.config import settings

    return {
        "status": "ready",
        "local_documents": len(load_documents()),
        "provider": "mock" if settings.mock_mode else settings.llm_provider,
    }
