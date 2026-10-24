"""Offline-first educational medical retrieval API."""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.api.routes_accounts import router as accounts_router
from app.api.routes_health import router as health_router
from app.api.routes_ingestion import router as ingestion_router
from app.api.routes_qa import router as qa_router
from app.config import settings
from app.observability.logging import configure_logging
from app.observability.metrics import elapsed_ms
from app.services.account_service import initialize_account_store

logger = configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_app):
    initialize_account_store()
    yield


app = FastAPI(
    title="Educational Medical RAG API",
    version="2.0.0",
    description="Evidence retrieval for educational information. Not a clinical decision-support, diagnosis, prescription, or emergency-response tool.",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(accounts_router)
app.include_router(qa_router)
app.include_router(ingestion_router)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Do not echo submitted values: malformed requests can contain sensitive text.
    errors = [
        {
            "loc": error.get("loc", ()),
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": errors})


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id = "".join(c for c in request_id[:100] if c.isalnum() or c in "-_.") or str(
        uuid.uuid4()
    )
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
        logger.error(
            "request_failed request_id=%s endpoint=%s error_category=internal",
            request_id,
            request.url.path,
        )
    response.headers["X-Request-ID"] = request_id
    if response.status_code >= 400:
        error_category = "validation" if response.status_code == 422 else "http_error"
        logger.info(
            "request_error request_id=%s endpoint=%s status=%s error_category=%s",
            request_id,
            request.url.path,
            response.status_code,
            error_category,
        )
    logger.info(
        "request_complete request_id=%s endpoint=%s method=%s status=%s retrieval_count=%s latency_ms=%.2f",
        request_id,
        request.url.path,
        request.method,
        response.status_code,
        getattr(request.state, "retrieval_count", 0),
        elapsed_ms(started),
    )
    return response
