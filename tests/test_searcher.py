import shutil
from pathlib import Path
import pytest
from gw_docs_mcp.indexer import Indexer
from gw_docs_mcp.searcher import Searcher, SearchResult


def _build_index(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    indexer = Indexer(temp_config)
    indexer.index_directory(pdf_dir)


def test_search_returns_results(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    searcher = Searcher(temp_config)
    results = searcher.search("RowIterator editable", top_k=3)
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)


def test_search_result_has_required_fields(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    searcher = Searcher(temp_config)
    results = searcher.search("query", top_k=1)
    r = results[0]
    assert isinstance(r.text, str) and len(r.text) > 0
    assert isinstance(r.source, str)
    assert isinstance(r.page, int)
    assert isinstance(r.score, float)


def test_search_respects_top_k(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    searcher = Searcher(temp_config)
    results = searcher.search("query", top_k=1)
    assert len(results) <= 1


def test_list_docs_returns_indexed_files(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    searcher = Searcher(temp_config)
    docs = searcher.list_docs()
    assert len(docs) >= 1
    sources = [d["source"] for d in docs]
    assert sample_pdf.name in sources


def test_list_docs_includes_chunk_count(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    searcher = Searcher(temp_config)
    docs = searcher.list_docs()
    for d in docs:
        assert "chunks" in d
        assert d["chunks"] > 0


def test_search_empty_index(tmp_path, mock_embedder, temp_config):
    searcher = Searcher(temp_config)
    results = searcher.search("anything", top_k=5)
    assert results == []
