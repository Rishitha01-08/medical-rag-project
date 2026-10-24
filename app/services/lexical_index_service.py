"""Persistent SQLite FTS5 keyword index used alongside Qdrant dense search."""

import json
import sqlite3
from pathlib import Path

from app.retrieval.bm25_retriever import tokenize
from app.services.index_manifest import expected_chunk_count

INDEX_PATH = Path("data/local/lexical_index.sqlite3")


def _connect(path=INDEX_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    return db


def rebuild_index(jsonl_paths, path=INDEX_PATH):
    db = _connect(path)
    try:
        db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5("
            "chunk_id UNINDEXED, title, source, section UNINDEXED, source_url UNINDEXED, "
            "page_number UNINDEXED, content, tokenize='unicode61')"
        )
        seen_ids = set()
        indexed_count = 0
        with db:
            db.execute("DELETE FROM chunks")
            for source_path in jsonl_paths:
                source = Path(source_path)
                if not source.exists():
                    continue
                with source.open(encoding="utf-8") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        chunk_id = row.get("chunk_id", "")
                        if not chunk_id or chunk_id in seen_ids:
                            continue
                        seen_ids.add(chunk_id)
                        db.execute(
                            "INSERT INTO chunks(chunk_id,title,source,section,source_url,page_number,content) "
                            "VALUES(?,?,?,?,?,?,?)",
                            (
                                chunk_id,
                                row.get("title", ""),
                                row.get("source", ""),
                                row.get("section", "") or "",
                                row.get("source_url", "") or "",
                                str(row.get("page_number") or ""),
                                row.get("content", ""),
                            ),
                        )
                        indexed_count += 1
    finally:
        db.close()
    return indexed_count


def search_keyword(query, limit=5, path=INDEX_PATH):
    terms = list(dict.fromkeys(tokenize(query)))
    if not terms:
        return []
    match_query = " OR ".join(f'"{term}"' for term in terms)
    db = _connect(path)
    try:
        rows = db.execute(
            "SELECT chunk_id,title,source,section,source_url,page_number,content,bm25(chunks) AS rank_score "
            "FROM chunks WHERE chunks MATCH ? ORDER BY rank_score LIMIT ?",
            (match_query, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            raise RuntimeError(
                "Keyword index is missing. Run scripts/index_vector_store.py first."
            ) from None
        raise
    finally:
        db.close()
    return [
        {
            **dict(row),
            "page_number": int(row["page_number"]) if row["page_number"] else None,
            "score": 1.0 / (1.0 + abs(float(row["rank_score"]))),
            "retrieval_source": "sqlite_fts5_bm25",
            "rank": rank,
        }
        for rank, row in enumerate(rows, 1)
    ]


def keyword_index_ready(path=INDEX_PATH):
    expected = expected_chunk_count()
    if expected is None:
        return False
    return keyword_index_count(path) == expected


def keyword_index_count(path=INDEX_PATH):
    db = _connect(path)
    try:
        row = db.execute("SELECT count(*) AS total FROM chunks").fetchone()
        return int(row["total"])
    except sqlite3.OperationalError:
        return 0
    finally:
        db.close()


def keyword_index_ids(path=INDEX_PATH):
    db = _connect(path)
    try:
        return {row["chunk_id"] for row in db.execute("SELECT chunk_id FROM chunks")}
    except sqlite3.OperationalError:
        return set()
    finally:
        db.close()
