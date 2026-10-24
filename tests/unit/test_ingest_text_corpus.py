from scripts.ingest_text_corpus import _is_heading, chunk_text, clean_text


def test_chunker_preserves_lines_and_heading_metadata():
    text = clean_text("CHAPTER 1\nA sentence about anatomy.\n\nA second paragraph follows.")
    chunks = list(chunk_text(text, size=6, overlap=2))

    assert "\n" in chunks[0][0]
    assert chunks[0][1] == "CHAPTER 1"
    assert all(len(content.split()) <= 6 for content, _ in chunks)


def test_chunker_does_not_emit_overlap_only_tail():
    chunks = list(chunk_text("one two three four five six", size=6, overlap=2))

    assert len(chunks) == 1
    assert chunks[0][0] == "one two three four five six"


def test_chunker_overlap_retains_boundary_words():
    chunks = list(chunk_text("one two three four five six seven", size=5, overlap=2))

    assert [content.split() for content, _ in chunks] == [
        ["one", "two", "three", "four", "five"],
        ["four", "five", "six", "seven"],
    ]


def test_heading_detection_ignores_uppercase_cover_text():
    assert _is_heading("CHAPTER 1 Anatomy")
    assert not _is_heading("CLINICAL MEDICINE HANDBOOK")
