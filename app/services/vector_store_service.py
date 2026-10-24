"""FastEmbed embeddings and Qdrant dense-vector operations."""

import json
import os
import uuid
from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from app.config import settings
from app.services.index_manifest import expected_chunk_count

VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5


@lru_cache(maxsize=1)
def get_client():
    if settings.vector_db_url.casefold() in {"embedded", "local"}:
        return QdrantClient(path="data/local/qdrant")
    return QdrantClient(url=settings.vector_db_url, api_key=settings.qdrant_api_key or None)


@lru_cache(maxsize=1)
def get_embedding_model():
    threads = min(8, os.cpu_count() or 4)
    return TextEmbedding(
        model_name=settings.embedding_model,
        cache_dir=settings.embedding_cache_dir or None,
        threads=threads,
    )


def ensure_collection(client=None, recreate=False):
    client = client or get_client()
    exists = client.collection_exists(settings.vector_collection)
    if exists and recreate:
        client.delete_collection(settings.vector_collection)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=settings.vector_collection,
            vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance.COSINE),
        )
        # Current queries do not filter on payload fields. Avoid a payload
        # index here so embedded and server-backed Qdrant behave consistently.
    return client


def search_dense(question, limit=5):
    client = get_client()
    if not client.collection_exists(settings.vector_collection):
        raise RuntimeError("Qdrant collection is missing. Run scripts/index_vector_store.py first.")
    vector = next(iter(get_embedding_model().embed([question]))).tolist()
    response = client.query_points(
        collection_name=settings.vector_collection,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    results = []
    for rank, point in enumerate(response.points, 1):
        payload = point.payload or {}
        results.append(
            {
                **payload,
                "score": float(point.score or 0.0),
                "retrieval_source": "qdrant_dense",
                "rank": rank,
            }
        )
    return results


def index_jsonl_files(paths, batch_size=64, recreate=False):
    client = ensure_collection(recreate=recreate)
    model = get_embedding_model()
    batch = []
    total = 0
    batches_uploaded = 0
    known_chunk_ids = set()
    if not recreate:
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=settings.vector_collection,
                limit=1000,
                offset=offset,
                with_payload=["chunk_id"],
                with_vectors=False,
            )
            known_chunk_ids.update(
                point.payload["chunk_id"]
                for point in points
                if point.payload and point.payload.get("chunk_id")
            )
            if offset is None:
                break

    def upload(rows):
        vectors = model.embed([row["content"] for row in rows])
        points = [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, row["chunk_id"])),
                vector=vector.tolist(),
                payload=row,
            )
            for row, vector in zip(rows, vectors, strict=True)
        ]
        client.upsert(collection_name=settings.vector_collection, points=points, wait=True)
        known_chunk_ids.update(row["chunk_id"] for row in rows)

    for source_path in paths:
        path = Path(source_path)
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("chunk_id") in known_chunk_ids:
                    continue
                batch.append(row)
                if len(batch) >= batch_size:
                    upload(batch)
                    total += len(batch)
                    batches_uploaded += 1
                    if batches_uploaded % 10 == 0:
                        print(f"Embedded and stored {total:,} new chunks...", flush=True)
                    batch = []
    if batch:
        upload(batch)
        total += len(batch)
        batches_uploaded += 1
        print(f"Embedded and stored {total:,} new chunks...", flush=True)
    return total


def vector_store_ready():
    client = get_client()
    if not client.collection_exists(settings.vector_collection):
        return False
    expected = expected_chunk_count()
    if expected is None:
        return False
    return (client.get_collection(settings.vector_collection).points_count or 0) == expected


def vector_store_count():
    client = get_client()
    if not client.collection_exists(settings.vector_collection):
        return 0
    return int(client.get_collection(settings.vector_collection).points_count or 0)


def vector_store_chunk_ids():
    """Return stored payload IDs for a full-build integrity check."""
    client = get_client()
    if not client.collection_exists(settings.vector_collection):
        return set()
    chunk_ids = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=settings.vector_collection,
            limit=1000,
            offset=offset,
            with_payload=["chunk_id"],
            with_vectors=False,
        )
        chunk_ids.update(
            point.payload["chunk_id"]
            for point in points
            if point.payload and point.payload.get("chunk_id")
        )
        if offset is None:
            return chunk_ids


def remove_unexpected_vector_chunks(allowed_chunk_ids):
    """Remove stale points not represented in the selected current JSONL inputs."""
    client = get_client()
    if not client.collection_exists(settings.vector_collection):
        return 0
    stale_point_ids = []
    removed = 0
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=settings.vector_collection,
            limit=1000,
            offset=offset,
            with_payload=["chunk_id"],
            with_vectors=False,
        )
        stale_point_ids.extend(
            point.id
            for point in points
            if not point.payload or point.payload.get("chunk_id") not in allowed_chunk_ids
        )
        if len(stale_point_ids) >= 1000 or offset is None:
            if stale_point_ids:
                client.delete(
                    collection_name=settings.vector_collection,
                    points_selector=models.PointIdsList(points=stale_point_ids),
                    wait=True,
                )
                removed += len(stale_point_ids)
                stale_point_ids = []
        if offset is None:
            return removed
