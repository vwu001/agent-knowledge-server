from pathlib import Path
from unittest.mock import MagicMock

import fitz
import numpy as np
import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "Guide.pdf"
    doc = fitz.open()

    page = doc.new_page()
    page.insert_text((50, 72), "RowIterator requires editable false on all read only list views.")
    page.insert_text((50, 100), "Omitting editable is a compile error in the schema.")

    page2 = doc.new_page()
    page2.insert_text((50, 72), "Use Query.make(entity.Foo) to create database queries.")
    page2.insert_text((50, 100), "Call orderByDescending on the select result, not the Query.")

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_markdown(tmp_path: Path) -> Path:
    md = tmp_path / "notes.md"
    md.write_text("# Notes\n\nThis is a markdown knowledge note.\n\n## Section\n\nMore content here.\n")
    return md


@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    txt = tmp_path / "plain.txt"
    txt.write_text("This is a plain text document about local knowledge indexing.")
    return txt


@pytest.fixture
def sample_html(tmp_path: Path) -> Path:
    html = tmp_path / "page.html"
    html.write_text(
        "<html><head><title>Example Page</title></head>"
        "<body><h1>Heading</h1><p>Useful HTML content.</p></body></html>"
    )
    return html


@pytest.fixture
def mock_embedder(monkeypatch):
    def fake_encode(texts, **kwargs):
        rng = np.random.RandomState(hash(tuple(texts)) & 0xFFFFFFFF)
        return rng.rand(len(texts), 384).astype("float32")

    mock = MagicMock()
    mock.encode.side_effect = fake_encode

    monkeypatch.setattr("local_knowledge_mcp.indexer.SentenceTransformer", lambda name, **kw: mock)
    monkeypatch.setattr("local_knowledge_mcp.searcher.SentenceTransformer", lambda name, **kw: mock)
    return mock


@pytest.fixture
def temp_config(tmp_path: Path):
    from local_knowledge_mcp.config import AppPaths, LocalKnowledgeConfig, ModelConfig, SearchConfig

    data_dir = tmp_path / "data"
    return LocalKnowledgeConfig(
        paths=AppPaths(
            config_path=tmp_path / "config.toml",
            data_dir=data_dir,
            sources_dir=data_dir / "sources",
            registry_path=data_dir / "sources" / "registry.json",
            chroma_dir=data_dir / "chroma",
            models_dir=data_dir / "models",
        ),
        search=SearchConfig(top_k=3, chunk_size=50, chunk_overlap=5),
        model=ModelConfig(name="all-MiniLM-L6-v2", cache_dir=str(data_dir / "models")),
    )
