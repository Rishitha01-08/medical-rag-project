"""Read the locally generated completeness manifest for search indexes."""

import json
from pathlib import Path

MANIFEST_PATH = Path("data/local/index_manifest.json")


def read_index_manifest(path=MANIFEST_PATH):
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        expected = int(manifest["expected_chunk_count"])
        if expected < 1:
            return None
        return manifest
    except (OSError, ValueError, KeyError, TypeError):
        return None


def expected_chunk_count(path=MANIFEST_PATH):
    manifest = read_index_manifest(path)
    return manifest["expected_chunk_count"] if manifest else None
