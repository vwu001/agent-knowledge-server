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


def test_chunk_text_raises_if_overlap_gte_chunk_size():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text here", chunk_size=10, overlap=10)


import shutil
import chromadb
from chromadb.config import Settings
from gw_docs_mcp.indexer import Indexer


def test_index_directory_creates_chunks(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)

    indexer = Indexer(temp_config)
    results = indexer.index_directory(pdf_dir)

    assert sample_pdf.name in results
    assert results[sample_pdf.name] > 0


def test_index_directory_stores_in_chromadb(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)

    indexer = Indexer(temp_config)
    indexer.index_directory(pdf_dir)

    client = chromadb.PersistentClient(
        path=temp_config.chroma.persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(temp_config.chroma.collection)
    count = collection.count()
    assert count > 0


def test_index_directory_upsert_is_idempotent(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)

    indexer = Indexer(temp_config)
    results1 = indexer.index_directory(pdf_dir)
    results2 = indexer.index_directory(pdf_dir)

    assert results1 == results2


def test_index_empty_directory(tmp_path, mock_embedder, temp_config):
    pdf_dir = tmp_path / "empty"
    pdf_dir.mkdir()
    indexer = Indexer(temp_config)
    results = indexer.index_directory(pdf_dir)
    assert results == {}
