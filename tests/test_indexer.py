from pathlib import Path
import pytest
from gw_docs_mcp.indexer import extract_pages, chunk_text, make_chunk_id


def test_extract_pages_returns_text(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert len(pages) == 2
    assert pages[0]["page"] == 0
    assert "RowIterator" in pages[0]["text"]
    assert pages[1]["page"] == 1
    assert "Query.make" in pages[1]["text"]


def test_extract_pages_includes_source(sample_pdf):
    pages = extract_pages(sample_pdf)
    assert pages[0]["source"] == sample_pdf.name


def test_chunk_text_splits_long_text():
    words = ["word"] * 200
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 50 for c in chunks)


def test_chunk_text_short_text_is_single_chunk():
    text = "short text here"
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_overlap():
    words = [f"w{i}" for i in range(100)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    # Second chunk should start with the last 5 words of the first chunk
    first_end = chunks[0].split()[-5:]
    second_start = chunks[1].split()[:5]
    assert first_end == second_start


def test_make_chunk_id_is_deterministic():
    id1 = make_chunk_id("MyDoc.pdf", 2, 3)
    id2 = make_chunk_id("MyDoc.pdf", 2, 3)
    assert id1 == id2
    assert id1 == "MyDoc.pdf::p2::c3"


def test_make_chunk_id_is_unique():
    assert make_chunk_id("a.pdf", 0, 0) != make_chunk_id("a.pdf", 0, 1)
    assert make_chunk_id("a.pdf", 0, 0) != make_chunk_id("b.pdf", 0, 0)
