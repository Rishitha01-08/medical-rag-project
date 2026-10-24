"""Document ingestion payload schema."""

from pydantic import Field

from app.schemas.common import StrictModel


class IngestDocument(StrictModel):
    document_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=20000)
    source: str = Field(default="user-provided educational material", max_length=500)
    source_url: str | None = None
    page_number: int | None = None
    section: str | None = None


class IngestionResponse(StrictModel):
    status: str
    document_id: str
    chunks_added: int
    dry_run: bool
