"""Embed the prepared JSONL chunks and build the hybrid search indexes."""

import argparse
import hashlib
import json
from pathlib import Path

from app.config import settings
from app.services.index_manifest import MANIFEST_PATH
from app.services.lexical_index_service import keyword_index_ids, rebuild_index
from app.services.vector_store_service import (
    index_jsonl_files,
    vector_store_chunk_ids,
    vector_store_count,
)

DEFAULT_INPUTS = [
    Path("data/sample/sample_medical_corpus.jsonl"),
    Path("data/local/documents.jsonl"),
    Path("data/local/hack_a_cure_chunks.jsonl"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", action="append", help="JSONL chunks file; repeat to include several"
    )
    parser.add_argument(
        "--recreate", action="store_true", help="Delete and rebuild the Qdrant collection"
    )
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    paths = [Path(path) for path in args.input] if args.input else DEFAULT_INPUTS
    expected_ids = set()
    source_names = []
    for path in paths:
        if not path.exists():
            continue
        source_names.append(str(path))
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                chunk_id = row.get("chunk_id")
                if not chunk_id:
                    parser.error(f"{path}:{line_number} has no chunk_id")
                expected_ids.add(chunk_id)
    if not expected_ids:
        parser.error("No indexed chunks found in the selected input files")
    if args.recreate:
        MANIFEST_PATH.unlink(missing_ok=True)

    count = index_jsonl_files(paths, batch_size=args.batch_size, recreate=args.recreate)
    lexical_count = rebuild_index(paths)
    vector_count = vector_store_count()
    expected_count = len(expected_ids)
    vector_ids = vector_store_chunk_ids()
    lexical_ids = keyword_index_ids()
    if vector_count != expected_count or lexical_count != expected_count or vector_ids != expected_ids or lexical_ids != expected_ids:
        raise SystemExit(
            "Index is incomplete or contains stale/missing chunk IDs: "
            f"expected={expected_count}, vectors={vector_count}/{len(vector_ids)} IDs, "
            f"keyword={lexical_count}/{len(lexical_ids)} IDs. "
            "If the corpus or chunker changed, rerun with --recreate."
        )
    manifest = {
        "expected_chunk_count": expected_count,
        "chunk_ids_sha256": hashlib.sha256("\n".join(sorted(expected_ids)).encode()).hexdigest(),
        "chunker_version": "preserve-lines-v2",
        "embedding_model": settings.embedding_model,
        "vector_collection": settings.vector_collection,
        "sources": source_names,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary_manifest.replace(MANIFEST_PATH)
    print(
        f"Indexed {count} new chunks; verified {expected_count} chunks in Qdrant and FTS5. "
        f"Wrote manifest to {MANIFEST_PATH}."
    )


if __name__ == "__main__":
    main()
