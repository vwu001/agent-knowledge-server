import shutil
import pytest
from gw_docs_mcp.server import handle_search, handle_list, handle_reindex


def _build_index(tmp_path, sample_pdf, mock_embedder, temp_config):
    from gw_docs_mcp.indexer import Indexer
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    Indexer(temp_config).index_directory(pdf_dir)
    return pdf_dir


def test_handle_search_returns_text(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    result = handle_search({"query": "RowIterator"}, temp_config)
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_search_includes_source(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    result = handle_search({"query": "RowIterator", "top_k": 1}, temp_config)
    assert ".pdf" in result


def test_handle_search_empty_index_returns_message(tmp_path, mock_embedder, temp_config):
    result = handle_search({"query": "anything"}, temp_config)
    assert "No documents indexed" in result


def test_handle_list_returns_text(tmp_path, sample_pdf, mock_embedder, temp_config):
    _build_index(tmp_path, sample_pdf, mock_embedder, temp_config)
    result = handle_list({}, temp_config)
    assert sample_pdf.name in result
    assert "chunks" in result


def test_handle_list_empty_returns_message(tmp_path, mock_embedder, temp_config):
    result = handle_list({}, temp_config)
    assert "No documents indexed" in result


def test_handle_reindex(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)
    result = handle_reindex({}, temp_config)
    assert sample_pdf.name in result
