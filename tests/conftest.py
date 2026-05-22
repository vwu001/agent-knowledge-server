import fitz
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a small test PDF with known GW-style content."""
    pdf_path = tmp_path / "TestDoc.pdf"
    doc = fitz.open()

    page = doc.new_page()
    page.insert_text((50, 72), "RowIterator requires editable='false' on all read-only list views.")
    page.insert_text((50, 100), "Omitting editable is a compile error in PCF schema.")

    page2 = doc.new_page()
    page2.insert_text((50, 72), "Use Query.make(entity.Foo) to create database queries.")
    page2.insert_text((50, 100), "Call orderByDescending on the select() result, not on the Query.")

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def mock_embedder(monkeypatch):
    """Replace SentenceTransformer with a fast deterministic fake."""
    def fake_encode(texts, **kwargs):
        rng = np.random.RandomState(hash(tuple(texts)) & 0xFFFFFFFF)
        return rng.rand(len(texts), 384).astype("float32")

    mock = MagicMock()
    mock.encode.side_effect = fake_encode

    monkeypatch.setattr("gw_docs_mcp.indexer.SentenceTransformer", lambda name, **kw: mock)
    monkeypatch.setattr("gw_docs_mcp.searcher.SentenceTransformer", lambda name, **kw: mock)
    return mock


@pytest.fixture
def temp_config(tmp_path: Path):
    """Return a GwDocsConfig pointing at tmp_path directories."""
    from gw_docs_mcp.config import GwDocsConfig, DocsConfig, SearchConfig, ModelConfig, ChromaConfig
    return GwDocsConfig(
        docs=DocsConfig(pdf_dir=str(tmp_path / "pdfs")),
        search=SearchConfig(top_k=3, chunk_size=50, chunk_overlap=5),
        model=ModelConfig(name="all-MiniLM-L6-v2", cache_dir=str(tmp_path / "models")),
        chroma=ChromaConfig(
            persist_dir=str(tmp_path / "chroma"),
            collection="test_gw_docs",
        ),
    )
