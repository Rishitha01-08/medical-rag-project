import json
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.schemas.documents import IngestDocument, IngestionResponse
from app.services.ingestion_service import prepare_document

router = APIRouter(prefix="/api/v1/documents", tags=["ingestion"])
LOCAL_STORE_PATH = Path("data/local/documents.jsonl")


@router.post(
    "/ingest",
    summary="Ingest educational source material",
    description="Chunks and persists an educational document to the local JSONL store. Configure INGESTION_API_KEY to require X-API-Key.",
    response_model=IngestionResponse,
)
def ingest(doc: IngestDocument, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    if settings.ingestion_api_key and x_api_key != settings.ingestion_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    path = LOCAL_STORE_PATH
    chunks = prepare_document(doc.model_dump(), settings.chunk_size, settings.chunk_overlap)
    existing = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["chunk_id"])
    added = [chunk for chunk in chunks if chunk["chunk_id"] not in existing]
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            for chunk in added:
                stream.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return {
        "status": "ingested",
        "document_id": doc.document_id,
        "chunks_added": len(added),
        "dry_run": False,
    }
