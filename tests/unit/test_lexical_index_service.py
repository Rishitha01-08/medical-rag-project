import json
from pathlib import Path
from uuid import uuid4

from app.services.lexical_index_service import keyword_index_ids, rebuild_index, search_keyword


def test_rebuild_fts_for_only_already_embedded_chunk_ids():
    suffix = uuid4().hex
    source = Path("data/local") / f"lexical-input-{suffix}.jsonl"
    index = Path("data/local") / f"lexical-index-{suffix}.sqlite3"
    rows = [
        {"chunk_id": "keep-this", "title": "Example", "content": "hydration water education"},
        {"chunk_id": "skip-this", "title": "Other", "content": "sleep routine education"},
    ]
    try:
        source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

        count = rebuild_index([source], path=index, chunk_ids={"keep-this"})

        assert count == 1
        assert keyword_index_ids(index) == {"keep-this"}
        assert [hit["chunk_id"] for hit in search_keyword("hydration", path=index)] == ["keep-this"]
    finally:
        source.unlink(missing_ok=True)
        index.unlink(missing_ok=True)
