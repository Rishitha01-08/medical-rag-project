"""Deterministic chunking and JSONL document ingestion."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def chunk_text(text, size=180, overlap=30):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and greater than non-negative overlap")
    words = text.split()
    step = size - overlap
    return [
        " ".join(words[i : i + size]) for i in range(0, len(words), step) if words[i : i + size]
    ]


def prepare_document(document, size=180, overlap=30, timestamp=None):
    content = str(document.get("content", "")).strip()
    document_id = str(document["document_id"])
    stamp = timestamp or datetime.now(UTC).isoformat()
    chunks, seen = [], set()
    for index, text in enumerate(chunk_text(content, size, overlap)):
        if not text or text in seen:
            continue
        seen.add(text)
        chunk_id = hashlib.sha256(f"{document_id}\0{index}\0{text}".encode()).hexdigest()[:24]
        chunks.append(
            {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "title": document.get("title", document_id),
                "source": document.get("source", "local educational material"),
                "source_url": document.get("source_url"),
                "page_number": document.get("page_number"),
                "section": document.get("section"),
                "content_hash": hashlib.sha256(text.encode()).hexdigest(),
                "ingestion_timestamp": stamp,
                "content": text,
            }
        )
    return chunks


def ingest_jsonl(path, output, dry_run=False, size=180, overlap=30):
    destination = Path(output)
    prior = []
    if destination.exists() and not dry_run:
        prior = [
            json.loads(line)
            for line in destination.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    all_chunks = list(prior)
    ids = {item["chunk_id"] for item in all_chunks}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        if not str(doc.get("content", "")).strip():
            continue
        for chunk in prepare_document(doc, size, overlap):
            if chunk["chunk_id"] not in ids:
                ids.add(chunk["chunk_id"])
                all_chunks.append(chunk)
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in all_chunks),
            encoding="utf-8",
        )
    return all_chunks
