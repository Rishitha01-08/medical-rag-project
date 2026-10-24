import json
from pathlib import Path
from uuid import uuid4

from app.services import vector_store_service
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


def test_partial_finalizer_can_remove_legacy_vector_ids(monkeypatch):
    class Point:
        def __init__(self, point_id, payload):
            self.id = point_id
            self.payload = payload

    class Client:
        def __init__(self):
            self.pages = [
                ([Point("one", {"chunk_id": "keep"}), Point("two", {"chunk_id": "stale"})], "two"),
                ([Point("three", None)], None),
            ]
            self.deleted = []

        def collection_exists(self, _collection):
            return True

        def scroll(self, **_kwargs):
            return self.pages.pop(0)

        def delete(self, **kwargs):
            self.deleted.extend(kwargs["points_selector"].points)

    client = Client()
    monkeypatch.setattr(vector_store_service, "get_client", lambda: client)
    removed = vector_store_service.remove_unexpected_vector_chunks({"keep"})

    assert removed == 2
    assert client.deleted == ["two", "three"]
