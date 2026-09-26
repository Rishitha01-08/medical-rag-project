from pathlib import Path
from uuid import uuid4

from app.services.grounding_service import citation_support, citations_for
from app.services.ingestion_service import chunk_text, ingest_jsonl, prepare_document


def test_chunking_and_stable_chunk_ids():
    doc = {"document_id": "d", "title": "Synthetic", "content": "one two three four five"}
    first = prepare_document(doc, 3, 1, timestamp="fixed")
    second = prepare_document(doc, 3, 1, timestamp="fixed")
    assert [item["chunk_id"] for item in first] == [item["chunk_id"] for item in second]
    assert chunk_text("one two three four", 2, 0) == ["one two", "three four"]


def test_invalid_chunk_parameters_and_duplicate_removal():
    try:
        chunk_text("some text", 2, 2)
    except ValueError:
        pass
    else:
        raise AssertionError("overlap equal to chunk size must be rejected")
    document = {"document_id": "d", "content": "same words same words"}
    chunks = prepare_document(document, 2, 0, timestamp="fixed")
    assert len({chunk["content"] for chunk in chunks}) == len(chunks)


def test_ingestion_dry_run_prepares_chunks_without_writing():
    output = Path("data/local") / f"dry-run-{uuid4().hex}.jsonl"
    try:
        rows = ingest_jsonl("tests/fixtures/corpus.jsonl", output, dry_run=True)
        assert rows
        assert not output.exists()
    finally:
        output.unlink(missing_ok=True)


def test_citation_support_only_accepts_retrieved_chunk_ids():
    retrieved = [{"chunk_id": "valid", "content": "supported evidence", "title": "Example"}]
    assert (
        citation_support([["valid"], ["fabricated"], ["valid", "fabricated"]], retrieved) == 1 / 3
    )
    assert citations_for(retrieved)[0]["source_id"] == "valid"
