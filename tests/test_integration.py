"""
End-to-end: index a real PDF-like document (created with PyMuPDF),
run a semantic search, verify we get back relevant content.
Uses the real embedding model — skipped unless GW_DOCS_INTEGRATION=1.
Set GW_DOCS_INTEGRATION=1 to run locally.
"""
import os
import shutil
import pytest
import fitz
from pathlib import Path

INTEGRATION = os.environ.get("GW_DOCS_INTEGRATION") == "1"
skip_unless_integration = pytest.mark.skipif(
    not INTEGRATION, reason="Set GW_DOCS_INTEGRATION=1 to run integration tests"
)


@pytest.fixture
def gw_style_pdf(tmp_path: Path) -> Path:
    """Create a small test PDF with GW-style content for integration testing."""
    pdf_path = tmp_path / "PCFGuide.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 72), "RowIterator must have editable='false' in read-only list views.")
        page.insert_text((50, 100), "Omitting editable attribute causes a PCF compile error.")
        page.insert_text((50, 128), "TextCell supports fontColor but Row element does not.")
        page2 = doc.new_page()
        page2.insert_text((50, 72), "Query.make(entity.Foo) creates a database query.")
        page2.insert_text((50, 100), "Call orderByDescending on the select() result object.")
        doc.save(str(pdf_path))
    return pdf_path


@skip_unless_integration
def test_full_pipeline_search_finds_relevant_content(tmp_path, gw_style_pdf, temp_config):
    """Index a PDF and verify semantic search finds relevant content."""
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(gw_style_pdf, pdf_dir / gw_style_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)

    from gw_docs_mcp.indexer import Indexer
    from gw_docs_mcp.searcher import Searcher

    Indexer(temp_config).index_directory(pdf_dir)
    results = Searcher(temp_config).search("how to make a list view read only", top_k=3)

    assert len(results) > 0
    combined = " ".join(r.text for r in results).lower()
    assert "rowiterator" in combined or "editable" in combined


@skip_unless_integration
def test_full_pipeline_list_shows_indexed_pdf(tmp_path, gw_style_pdf, temp_config):
    """Index a PDF and verify list_docs shows the indexed file."""
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(gw_style_pdf, pdf_dir / gw_style_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)

    from gw_docs_mcp.indexer import Indexer
    from gw_docs_mcp.searcher import Searcher

    Indexer(temp_config).index_directory(pdf_dir)
    docs = Searcher(temp_config).list_docs()

    assert any(d["source"] == gw_style_pdf.name for d in docs)
