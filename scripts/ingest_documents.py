"""Ingest JSONL documents into ignored local storage."""

import argparse

from app.config import settings
from app.services.ingestion_service import ingest_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input JSONL path")
    parser.add_argument("--output", default="data/local/documents.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = ingest_jsonl(
        args.input, args.output, args.dry_run, settings.chunk_size, settings.chunk_overlap
    )
    print(f"Prepared {len(result)} unique chunks (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()
