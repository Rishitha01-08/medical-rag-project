"""Normalize supplied textbook text, preserve line structure, and make auditable chunks."""

import argparse
import hashlib
import io
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_SOURCE = Path("data/raw/hack-a-cure")
DEFAULT_OUTPUT = Path("data/local/hack_a_cure_chunks.jsonl")
AUDIT_OUTPUT = Path("data/local/corpus_audit.json")
CHUNKER_VERSION = "preserve-lines-v2"
HEADING_PATTERN = re.compile(r"^(?:chapter|unit|section|part|appendix|contents|index)\b", re.I)


def clean_text(text):
    """Normalize Unicode/spacing without flattening paragraph or line boundaries."""
    text = unicodedata.normalize("NFKC", text).replace("\x00", " ").replace("\f", "\n\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufffd", " ")
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_heading(line):
    label = line.strip()
    return bool(label and len(label) <= 140 and HEADING_PATTERN.match(label))


def chunk_text(text, size=180, overlap=30):
    """Yield overlapping word windows as original text slices, including line breaks."""
    if size < 1 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and greater than the overlap")
    step = size - overlap
    window = []
    section = None
    new_since_emit = 0
    for line in io.StringIO(text):
        line = line.rstrip("\n")
        if _is_heading(line):
            section = line.strip()[:140]
        words = line.split()
        for word_index, word in enumerate(words):
            separator = "\n" if word_index == 0 and window else " "
            window.append((separator, word, section))
            new_since_emit += 1
            if len(window) == size:
                yield "".join(item[0] + item[1] for item in window).strip(), window[0][2]
                window = window[step:]
                new_since_emit = 0
    if window and new_since_emit:
        yield "".join(item[0] + item[1] for item in window).strip(), window[0][2]


def ingest_directory(source_dir=DEFAULT_SOURCE, output=DEFAULT_OUTPUT, size=180, overlap=30):
    source_dir, output = Path(source_dir), Path(output)
    source_files = sorted(source_dir.glob("*.txt"))
    if not source_files:
        raise FileNotFoundError(f"No .txt corpus files found in {source_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_suffix(output.suffix + ".tmp")
    count = 0
    seen_content_hashes = set()
    audit = {
        "created_at": datetime.now(UTC).isoformat(),
        "chunker_version": CHUNKER_VERSION,
        "chunk_size_words": size,
        "overlap_words": overlap,
        "input_files": [],
        "total_chunks": 0,
        "duplicate_chunk_content": 0,
        "limitations": [
            "Inputs are UTF-8 text extracts; source page numbers/layout were not present.",
            "Replacement characters in source text were changed to spaces; missing source characters cannot be recovered.",
            "Fixed word windows are a baseline, not clinically validated chunk boundaries.",
        ],
    }
    try:
        with temp_output.open("w", encoding="utf-8", newline="\n") as stream:
            for path in source_files:
                raw = path.read_text(encoding="utf-8", errors="replace")
                damaged_characters = raw.count("\ufffd")
                text = clean_text(raw)
                document_id = "hack-a-cure-" + re.sub(
                    r"[^a-z0-9]+", "-", path.stem.casefold()
                ).strip("-")
                stamp = datetime.now(UTC).isoformat()
                file_chunks = 0
                for index, (content, section) in enumerate(chunk_text(text, size, overlap)):
                    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    if content_hash in seen_content_hashes:
                        audit["duplicate_chunk_content"] += 1
                    seen_content_hashes.add(content_hash)
                    chunk_id = hashlib.sha256(
                        f"{CHUNKER_VERSION}\0{document_id}\0{index}\0{content}".encode()
                    ).hexdigest()[:24]
                    row = {
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "chunk_index": index,
                        "chunker_version": CHUNKER_VERSION,
                        "title": path.stem.replace("&", " & "),
                        "source": f"Hack-A-Cure supplied dataset: {path.name}",
                        "source_file": path.name,
                        "source_url": None,
                        "page_number": None,
                        "section": section,
                        "content_hash": content_hash,
                        "ingestion_timestamp": stamp,
                        "content": content,
                    }
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                    count += 1
                    file_chunks += 1
                audit["input_files"].append(
                    {
                        "file": path.name,
                        "bytes": path.stat().st_size,
                        "characters": len(raw),
                        "replacement_characters": damaged_characters,
                        "chunk_count": file_chunks,
                    }
                )
        temp_output.replace(output)
        audit["total_chunks"] = count
        audit_path = output.parent / AUDIT_OUTPUT.name
        audit_temp = audit_path.with_suffix(audit_path.suffix + ".tmp")
        audit_temp.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        audit_temp.replace(audit_path)
    finally:
        temp_output.unlink(missing_ok=True)
    return len(source_files), count, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--chunk-size", type=int, default=180, help="Maximum words per chunk")
    parser.add_argument("--overlap", type=int, default=30, help="Overlapping words between chunks")
    args = parser.parse_args()
    files, chunks, output = ingest_directory(args.source, args.output, args.chunk_size, args.overlap)
    print(f"Chunked {files} text files into {chunks} chunks at {output}")
    print(f"Wrote corpus quality audit to {output.parent / AUDIT_OUTPUT.name}")


if __name__ == "__main__":
    main()
