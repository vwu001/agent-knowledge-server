# gw-docs-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Claude Code plugin that provides local semantic search over Guidewire PDF documentation via three MCP tools — fully offline after initial model download.

**Architecture:** A Python package with five modules: `config` (TOML read/write), `indexer` (PDF→chunks→embeddings→ChromaDB), `searcher` (ChromaDB query wrapper), `server` (MCP stdio server), and `cli` (configure/index/status/serve commands). The MCP server is wired into Claude Code via `claude-plugin.json` and runs as a background stdio process.

**Tech Stack:** Python 3.11+, `mcp` SDK, `pymupdf`, `sentence-transformers` (all-MiniLM-L6-v2), `chromadb`, `typer`, `pytest`

**Repo:** `https://github.com/vwu001/gw-docs-mcp` — checked out at `/Users/vincentwu/dev/aibuild/tools/gw-docs-mcp`

**Design spec:** `docs/2026-05-22-gw-docs-mcp-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package definition, dependencies, entry points |
| `.gitignore` | Ignore `__pycache__`, `.venv`, `*.egg-info` |
| `claude-plugin.json` | Claude Code plugin manifest — registers MCP server |
| `README.md` | Install and usage instructions |
| `src/gw_docs_mcp/__init__.py` | Package version |
| `src/gw_docs_mcp/config.py` | Read/write `~/.config/gw-docs-mcp/config.toml`, typed dataclass |
| `src/gw_docs_mcp/indexer.py` | Extract PDF text, chunk, embed, upsert into ChromaDB |
| `src/gw_docs_mcp/searcher.py` | Query ChromaDB, format results, list indexed docs |
| `src/gw_docs_mcp/server.py` | MCP stdio server with three tools |
| `src/gw_docs_mcp/cli.py` | Typer CLI: configure, index, status, serve |
| `tests/conftest.py` | Shared fixtures: sample PDF, mock embedder, temp config |
| `tests/test_config.py` | Config read/write/defaults |
| `tests/test_indexer.py` | PDF extraction, chunking, index pipeline (mocked embedder) |
| `tests/test_searcher.py` | Search and list (mocked embedder, real ChromaDB) |
| `tests/test_server.py` | MCP tool logic (unit, no MCP protocol) |
| `tests/test_cli.py` | CLI commands via Typer test runner |
| `tests/test_integration.py` | End-to-end: index real PDF, search, verify results |

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/gw_docs_mcp/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gw-docs-mcp"
version = "1.0.0"
description = "Local semantic search over Guidewire PDF documentation for Claude"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "pymupdf>=1.24.0",
    "sentence-transformers>=3.0.0",
    "chromadb>=0.5.0",
    "typer>=0.12.0",
]

[project.scripts]
gw-docs-mcp = "gw_docs_mcp.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/gw_docs_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.egg-info/
.venv/
dist/
build/
.pytest_cache/
*.pyc
```

- [ ] **Step 3: Create `src/gw_docs_mcp/__init__.py`**

```python
__version__ = "1.0.0"
```

- [ ] **Step 4: Create `tests/__init__.py`**

```python
```

- [ ] **Step 5: Create `tests/conftest.py`**

```python
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
        rng = np.random.RandomState(42)
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
```

- [ ] **Step 6: Install dependencies and verify scaffold**

```bash
cd /Users/vincentwu/dev/aibuild/tools/gw-docs-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest pymupdf sentence-transformers chromadb typer mcp
python -c "import fitz, chromadb, typer, mcp; print('deps OK')"
```

Expected: `deps OK`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore src/ tests/
git commit -m "feat: project scaffold, deps, test fixtures"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/gw_docs_mcp/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
from pathlib import Path
import pytest
from gw_docs_mcp.config import GwDocsConfig, load_config, save_config, DEFAULT_CONFIG_PATH


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", tmp_path / "nonexistent.toml")
    cfg = load_config()
    assert cfg.search.top_k == 5
    assert cfg.search.chunk_size == 500
    assert cfg.search.chunk_overlap == 50
    assert cfg.model.name == "all-MiniLM-L6-v2"
    assert cfg.chroma.collection == "gw_docs"


def test_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    cfg.docs.pdf_dir = "/some/pdf/dir"
    save_config(cfg)
    reloaded = load_config()
    assert reloaded.docs.pdf_dir == "/some/pdf/dir"


def test_tilde_expansion(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    cfg.docs.pdf_dir = "~/my-pdfs"
    save_config(cfg)
    reloaded = load_config()
    assert reloaded.docs.pdf_dir == "~/my-pdfs"


def test_chroma_dir_is_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    assert isinstance(cfg.chroma.persist_dir, str)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` (config.py doesn't exist yet)

- [ ] **Step 3: Create `src/gw_docs_mcp/config.py`**

```python
from __future__ import annotations
import tomllib
import tomli_w
from dataclasses import dataclass, field, asdict
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "gw-docs-mcp" / "config.toml"


@dataclass
class DocsConfig:
    pdf_dir: str = ""


@dataclass
class SearchConfig:
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50


@dataclass
class ModelConfig:
    name: str = "all-MiniLM-L6-v2"
    cache_dir: str = str(Path.home() / ".gw-docs-mcp" / "models")


@dataclass
class ChromaConfig:
    persist_dir: str = str(Path.home() / ".gw-docs-mcp" / "chroma")
    collection: str = "gw_docs"


@dataclass
class GwDocsConfig:
    docs: DocsConfig = field(default_factory=DocsConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    chroma: ChromaConfig = field(default_factory=ChromaConfig)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> GwDocsConfig:
    if not path.exists():
        return GwDocsConfig()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return GwDocsConfig(
        docs=DocsConfig(**data.get("docs", {})),
        search=SearchConfig(**data.get("search", {})),
        model=ModelConfig(**data.get("model", {})),
        chroma=ChromaConfig(**data.get("chroma", {})),
    )


def save_config(cfg: GwDocsConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "docs": asdict(cfg.docs),
        "search": asdict(cfg.search),
        "model": asdict(cfg.model),
        "chroma": asdict(cfg.chroma),
    }
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
```

- [ ] **Step 4: Install `tomli_w` and add to deps**

```bash
pip install tomli-w
```

Add to `pyproject.toml` dependencies:
```toml
"tomli-w>=1.0.0",
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/gw_docs_mcp/config.py tests/test_config.py pyproject.toml
git commit -m "feat: config module with TOML read/write and typed dataclasses"
```

---

## Task 3: PDF Extraction and Chunking

**Files:**
- Create: `src/gw_docs_mcp/indexer.py` (extraction + chunking only — embedding in Task 4)
- Create: `tests/test_indexer.py` (extraction + chunking tests)

- [ ] **Step 1: Write failing tests for extraction and chunking**

```python
# tests/test_indexer.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_indexer.py -v
```

Expected: `ImportError` (indexer.py doesn't exist yet)

- [ ] **Step 3: Create `src/gw_docs_mcp/indexer.py` (extraction + chunking only)**

```python
from __future__ import annotations
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

from gw_docs_mcp.config import GwDocsConfig


def extract_pages(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract text from each page of a PDF. Returns list of {text, page, source}."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text().strip()
        if text:
            pages.append({
                "text": text,
                "page": page_num,
                "source": pdf_path.name,
            })
    doc.close()
    return pages


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def make_chunk_id(source: str, page: int, chunk_idx: int) -> str:
    """Deterministic chunk ID: 'filename::p{page}::c{idx}'."""
    return f"{source}::p{page}::c{chunk_idx}"


class Indexer:
    def __init__(self, cfg: GwDocsConfig) -> None:
        self.cfg = cfg
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(
                self.cfg.model.name,
                cache_folder=self.cfg.model.cache_dir,
            )
        return self._model

    def index_directory(self, pdf_dir: Path) -> dict[str, int]:
        """Index all PDFs in pdf_dir. Returns {filename: chunk_count}."""
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=self.cfg.chroma.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(self.cfg.chroma.collection)
        model = self._get_model()

        results: dict[str, int] = {}
        pdf_files = sorted(pdf_dir.glob("*.pdf"))

        for pdf_path in pdf_files:
            ids, embeddings, documents, metadatas = [], [], [], []
            pages = extract_pages(pdf_path)
            chunk_size = self.cfg.search.chunk_size
            overlap = self.cfg.search.chunk_overlap

            for page_data in pages:
                chunks = chunk_text(page_data["text"], chunk_size, overlap)
                texts = chunks
                vecs = model.encode(texts, show_progress_bar=False)
                for idx, (chunk, vec) in enumerate(zip(chunks, vecs)):
                    chunk_id = make_chunk_id(page_data["source"], page_data["page"], idx)
                    ids.append(chunk_id)
                    embeddings.append(vec.tolist())
                    documents.append(chunk)
                    metadatas.append({"source": page_data["source"], "page": page_data["page"]})

            if ids:
                collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
            results[pdf_path.name] = len(ids)

        return results
```

- [ ] **Step 4: Run extraction/chunking tests — verify they pass**

```bash
pytest tests/test_indexer.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/gw_docs_mcp/indexer.py tests/test_indexer.py
git commit -m "feat: PDF extraction, chunking, chunk ID generation"
```

---

## Task 4: Indexer — Embedding and ChromaDB Storage

**Files:**
- Modify: `tests/test_indexer.py` (add indexer integration tests)

- [ ] **Step 1: Add indexer integration tests**

Append to `tests/test_indexer.py`:

```python
import chromadb
from chromadb.config import Settings
from gw_docs_mcp.indexer import Indexer


def test_index_directory_creates_chunks(tmp_path, sample_pdf, mock_embedder, temp_config):
    # Put sample_pdf in the pdf_dir
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    import shutil
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)

    indexer = Indexer(temp_config)
    results = indexer.index_directory(pdf_dir)

    assert sample_pdf.name in results
    assert results[sample_pdf.name] > 0


def test_index_directory_stores_in_chromadb(tmp_path, sample_pdf, mock_embedder, temp_config):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    import shutil
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
    import shutil
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)

    indexer = Indexer(temp_config)
    indexer.index_directory(pdf_dir)
    results1 = indexer.index_directory(pdf_dir)
    results2 = indexer.index_directory(pdf_dir)

    assert results1 == results2


def test_index_empty_directory(tmp_path, mock_embedder, temp_config):
    pdf_dir = tmp_path / "empty"
    pdf_dir.mkdir()
    indexer = Indexer(temp_config)
    results = indexer.index_directory(pdf_dir)
    assert results == {}
```

- [ ] **Step 2: Run new tests — verify they pass**

```bash
pytest tests/test_indexer.py -v
```

Expected: 11 passed (7 from Task 3 + 4 new)

- [ ] **Step 3: Commit**

```bash
git add tests/test_indexer.py
git commit -m "feat: indexer ChromaDB storage tests — upsert, idempotent, empty dir"
```

---

## Task 5: Searcher

**Files:**
- Create: `src/gw_docs_mcp/searcher.py`
- Create: `tests/test_searcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_searcher.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_searcher.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `src/gw_docs_mcp/searcher.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from gw_docs_mcp.config import GwDocsConfig


@dataclass
class SearchResult:
    text: str
    source: str
    page: int
    score: float


class Searcher:
    def __init__(self, cfg: GwDocsConfig) -> None:
        self.cfg = cfg
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(
                self.cfg.model.name,
                cache_folder=self.cfg.model.cache_dir,
            )
        return self._model

    def _get_collection(self):
        client = chromadb.PersistentClient(
            path=self.cfg.chroma.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        return client.get_or_create_collection(self.cfg.chroma.collection)

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        k = top_k if top_k is not None else self.cfg.search.top_k
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        model = self._get_model()
        query_vec = model.encode([query], show_progress_bar=False)[0].tolist()
        raw = collection.query(query_embeddings=[query_vec], n_results=min(k, collection.count()))
        results = []
        for text, meta, distance in zip(
            raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
        ):
            results.append(SearchResult(
                text=text,
                source=meta["source"],
                page=int(meta["page"]),
                score=round(1.0 - distance, 4),
            ))
        return results

    def list_docs(self) -> list[dict[str, Any]]:
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        all_items = collection.get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in all_items["metadatas"]:
            counts[meta["source"]] = counts.get(meta["source"], 0) + 1
        return [{"source": src, "chunks": count} for src, count in sorted(counts.items())]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_searcher.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/gw_docs_mcp/searcher.py tests/test_searcher.py
git commit -m "feat: searcher with semantic search and list_docs"
```

---

## Task 6: MCP Server

**Files:**
- Create: `src/gw_docs_mcp/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_server.py
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
    assert "No documents indexed" in result or result == ""


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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_server.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `src/gw_docs_mcp/server.py`**

```python
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from gw_docs_mcp.config import GwDocsConfig, load_config
from gw_docs_mcp.indexer import Indexer
from gw_docs_mcp.searcher import Searcher

_server = Server("gw-docs")


def handle_search(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    query = arguments["query"]
    top_k = arguments.get("top_k", cfg.search.top_k)
    searcher = Searcher(cfg)
    results = searcher.search(query, top_k=top_k)
    if not results:
        return "No documents indexed yet. Run: gw-docs-mcp index"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.source} p.{r.page + 1} (score: {r.score})")
        lines.append(r.text)
        lines.append("")
    return "\n".join(lines).strip()


def handle_list(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    searcher = Searcher(cfg)
    docs = searcher.list_docs()
    if not docs:
        return "No documents indexed yet. Run: gw-docs-mcp index"
    lines = [f"{'Source':<40} {'Chunks':>6}"]
    lines.append("-" * 48)
    for d in docs:
        lines.append(f"{d['source']:<40} {d['chunks']:>6} chunks")
    return "\n".join(lines)


def handle_reindex(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    pdf_dir = Path(arguments.get("pdf_dir") or cfg.docs.pdf_dir).expanduser()
    if not pdf_dir.exists():
        return f"PDF directory not found: {pdf_dir}"
    indexer = Indexer(cfg)
    results = indexer.index_directory(pdf_dir)
    if not results:
        return f"No PDFs found in {pdf_dir}"
    lines = [f"Indexed {len(results)} file(s):"]
    for name, count in results.items():
        lines.append(f"  {name}: {count} chunks")
    return "\n".join(lines)


@_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_gw_docs",
            description="Semantically search indexed Guidewire PDF documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_gw_docs",
            description="List all indexed Guidewire PDFs and their chunk counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="reindex_gw_docs",
            description="Re-index GW PDFs from the configured directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_dir": {"type": "string", "description": "Override PDF directory path"},
                },
            },
        ),
    ]


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    cfg = load_config()
    if name == "search_gw_docs":
        text = handle_search(arguments, cfg)
    elif name == "list_gw_docs":
        text = handle_list(arguments, cfg)
    elif name == "reindex_gw_docs":
        text = handle_reindex(arguments, cfg)
    else:
        text = f"Unknown tool: {name}"
    return [TextContent(type="text", text=text)]


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_main())
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_server.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/gw_docs_mcp/server.py tests/test_server.py
git commit -m "feat: MCP server with search, list, reindex tools"
```

---

## Task 7: CLI

**Files:**
- Create: `src/gw_docs_mcp/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import shutil
from pathlib import Path
from typer.testing import CliRunner
from gw_docs_mcp.cli import app

runner = CliRunner()


def test_configure_writes_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr("gw_docs_mcp.cli.DEFAULT_CONFIG_PATH", config_path)
    result = runner.invoke(app, ["configure", "--pdf-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Saved" in result.output
    assert config_path.exists()


def test_configure_shows_saved_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr("gw_docs_mcp.cli.DEFAULT_CONFIG_PATH", config_path)
    result = runner.invoke(app, ["configure", "--pdf-dir", "/my/pdfs"])
    assert "/my/pdfs" in result.output


def test_index_command(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)

    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["index"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_index_command_with_override_dir(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["index", "--pdf-dir", str(pdf_dir)])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_status_shows_indexed_files(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    from gw_docs_mcp.indexer import Indexer
    Indexer(temp_config).index_directory(pdf_dir)
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_status_no_docs(tmp_path, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No documents" in result.output
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `src/gw_docs_mcp/cli.py`**

```python
from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer

from gw_docs_mcp.config import load_config, save_config, DEFAULT_CONFIG_PATH
from gw_docs_mcp.indexer import Indexer
from gw_docs_mcp.searcher import Searcher
from gw_docs_mcp.server import handle_list, handle_reindex

app = typer.Typer(help="gw-docs-mcp — local semantic search over Guidewire PDF docs")


@app.command()
def configure(
    pdf_dir: str = typer.Option(..., "--pdf-dir", help="Directory containing GW PDF files"),
):
    """Set the PDF directory and write config file."""
    cfg = load_config()
    cfg.docs.pdf_dir = pdf_dir
    save_config(cfg)
    typer.echo(f"Saved config to {DEFAULT_CONFIG_PATH}")
    typer.echo(f"  pdf_dir = {pdf_dir}")
    typer.echo("Next: run 'gw-docs-mcp index' to index your PDFs.")


@app.command()
def index(
    pdf_dir: Optional[str] = typer.Option(None, "--pdf-dir", help="Override configured PDF directory"),
):
    """Index all PDFs in the configured (or specified) directory."""
    cfg = load_config()
    target = Path(pdf_dir or cfg.docs.pdf_dir).expanduser()
    if not target.exists():
        typer.echo(f"Error: directory not found: {target}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Indexing PDFs in {target} ...")
    result = handle_reindex({"pdf_dir": str(target)}, cfg)
    typer.echo(result)


@app.command()
def status():
    """Show what is currently indexed."""
    cfg = load_config()
    result = handle_list({}, cfg)
    typer.echo(result)


@app.command()
def serve():
    """Start the MCP server (called by Claude Code automatically)."""
    from gw_docs_mcp.server import main
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: 6 passed

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: All tests pass (should be 24+ tests across all modules)

- [ ] **Step 6: Commit**

```bash
git add src/gw_docs_mcp/cli.py tests/test_cli.py
git commit -m "feat: CLI with configure, index, status, serve commands"
```

---

## Task 8: Plugin Manifest and README

**Files:**
- Create: `claude-plugin.json`
- Create: `README.md`

- [ ] **Step 1: Create `claude-plugin.json`**

```json
{
  "name": "gw-docs-mcp",
  "version": "1.0.0",
  "description": "Local semantic search over Guidewire PDF documentation for Claude",
  "servers": {
    "gw-docs": {
      "type": "stdio",
      "command": "gw-docs-mcp",
      "args": ["serve"],
      "description": "Search GW docs locally — fully offline after first model download"
    }
  }
}
```

- [ ] **Step 2: Create `README.md`**

````markdown
# gw-docs-mcp

Local semantic search over Guidewire PDF documentation for Claude. Fully offline after first model download (~90MB). Three MCP tools: `search_gw_docs`, `list_gw_docs`, `reindex_gw_docs`.

## Install

```bash
# 1. Clone and install
git clone https://github.com/vwu001/gw-docs-mcp
cd gw-docs-mcp
pip install -e .

# 2. Register with Claude Code (add to ~/.claude/settings.json)
{
  "mcpServers": {
    "gw-docs": {
      "command": "gw-docs-mcp",
      "args": ["serve"]
    }
  }
}

# 3. Point at your PDF directory
gw-docs-mcp configure --pdf-dir ~/path/to/gw-pdfs

# 4. Index (one-time, ~1-2 min per 100 pages, first run downloads ~90MB model)
gw-docs-mcp index

# 5. Verify
gw-docs-mcp status
```

## Tools Available in Claude

| Tool | Description |
|---|---|
| `search_gw_docs(query)` | Semantic search — returns top matching snippets with source + page |
| `list_gw_docs()` | Show what PDFs are indexed and how many chunks each has |
| `reindex_gw_docs()` | Re-index after adding new PDFs |

## Example Queries

```
search_gw_docs("RowIterator read-only list view")
search_gw_docs("Gosu for loop syntax")
search_gw_docs("entity retireable marker")
search_gw_docs("Query.make orderBy")
search_gw_docs("SearchPanel criteria serializable")
```

## Supported PDFs

Drop any Guidewire PDF into your configured directory and run `gw-docs-mcp index`. Works with:
- UserInterfaceConfig.pdf
- GosuRules.pdf / GosuRefGuide.pdf
- DataModelConfig.pdf
- ConfigPC.pdf
- WorkflowConfig.pdf
- ProductModelGuide.pdf

## Storage

All data is local:
- `~/.gw-docs-mcp/chroma/` — vector index (ChromaDB)
- `~/.gw-docs-mcp/models/` — embedding model cache
- `~/.config/gw-docs-mcp/config.toml` — configuration

## Re-indexing

When you add new PDFs:
```bash
gw-docs-mcp index
# or from within Claude: reindex_gw_docs()
```
````

- [ ] **Step 3: Verify install works end-to-end**

```bash
pip install -e .
gw-docs-mcp --help
```

Expected output:
```
Usage: gw-docs-mcp [OPTIONS] COMMAND [ARGS]...
  gw-docs-mcp — local semantic search over Guidewire PDF docs
Commands:
  configure  Set the PDF directory and write config file.
  index      Index all PDFs in the configured directory.
  serve      Start the MCP server.
  status     Show what is currently indexed.
```

- [ ] **Step 4: Commit**

```bash
git add claude-plugin.json README.md
git commit -m "feat: plugin manifest and README with install instructions"
```

---

## Task 9: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
"""
End-to-end: index a real PDF-like document (created with PyMuPDF),
run a semantic search, verify we get back relevant content.
Uses the real embedding model — skipped if model download would be needed
in CI. Set GW_DOCS_INTEGRATION=1 to run locally.
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
    pdf_path = tmp_path / "PCFGuide.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "RowIterator must have editable='false' in read-only list views.")
    page.insert_text((50, 100), "Omitting editable attribute causes a PCF compile error.")
    page.insert_text((50, 128), "TextCell supports fontColor but Row element does not.")
    page2 = doc.new_page()
    page2.insert_text((50, 72), "Query.make(entity.Foo) creates a database query.")
    page2.insert_text((50, 100), "Call orderByDescending on the select() result object.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@skip_unless_integration
def test_full_pipeline_search_finds_relevant_content(tmp_path, gw_style_pdf, temp_config):
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
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(gw_style_pdf, pdf_dir / gw_style_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)

    from gw_docs_mcp.indexer import Indexer
    from gw_docs_mcp.searcher import Searcher

    Indexer(temp_config).index_directory(pdf_dir)
    docs = Searcher(temp_config).list_docs()

    assert any(d["source"] == gw_style_pdf.name for d in docs)
```

- [ ] **Step 2: Run unit suite (integration tests skipped by default)**

```bash
pytest -v
```

Expected: All unit tests pass; integration tests skipped

- [ ] **Step 3: Run integration test locally with real model**

```bash
GW_DOCS_INTEGRATION=1 pytest tests/test_integration.py -v -s
```

Expected: Both integration tests pass (downloads model on first run, ~90MB)

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: integration tests (skipped by default, GW_DOCS_INTEGRATION=1 to run)"
```

---

## Task 10: Push and Wire Into Claude

**Files:**
- No new files — wire the installed package into Claude Code

- [ ] **Step 1: Push to GitHub**

```bash
git push -u origin main
```

- [ ] **Step 2: Verify package installs cleanly from scratch**

```bash
cd /tmp
pip install git+https://github.com/vwu001/gw-docs-mcp.git
gw-docs-mcp --help
```

Expected: Help text prints with all four commands

- [ ] **Step 3: Configure Claude Code MCP settings**

Edit `~/.claude/settings.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "gw-docs": {
      "command": "gw-docs-mcp",
      "args": ["serve"]
    }
  }
}
```

- [ ] **Step 4: Point at GW PDF directory**

```bash
gw-docs-mcp configure --pdf-dir /Users/vincentwu/Downloads
```

Expected:
```
Saved config to /Users/vincentwu/.config/gw-docs-mcp/config.toml
  pdf_dir = /Users/vincentwu/Downloads
Next: run 'gw-docs-mcp index' to index your PDFs.
```

- [ ] **Step 5: Index the GW docs**

```bash
gw-docs-mcp index
```

Expected (first run downloads model, then indexes):
```
Indexing PDFs in /Users/vincentwu/Downloads ...
Indexed 8 file(s):
  ConfigPC.pdf: 142 chunks
  DataModelConfig.pdf: 112 chunks
  GosuRefGuide.pdf: 98 chunks
  ...
```

- [ ] **Step 6: Verify status**

```bash
gw-docs-mcp status
```

Expected: Table showing each PDF with chunk count

- [ ] **Step 7: Restart Claude Code and verify tools are available**

Restart Claude Code, then in a new session run:
```
list_gw_docs()
```

Expected: Returns table of indexed PDFs

- [ ] **Step 8: Final commit and tag**

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Self-Review

**Spec coverage:**
- ✅ Three MCP tools: search_gw_docs, list_gw_docs, reindex_gw_docs (Tasks 6, 7)
- ✅ PyMuPDF extraction (Task 3)
- ✅ all-MiniLM-L6-v2 embeddings, offline (Task 3-4)
- ✅ ChromaDB local storage (Task 4-5)
- ✅ Config file at `~/.config/gw-docs-mcp/config.toml` (Task 2)
- ✅ CLI: configure, index, status, serve (Task 7)
- ✅ claude-plugin.json manifest (Task 8)
- ✅ README with install instructions (Task 8)
- ✅ Integration test (Task 9)
- ✅ Wire into Claude Code (Task 10)

**Placeholder scan:** No TBDs, no "implement later", all code is concrete.

**Type consistency:** `GwDocsConfig` used consistently across config, indexer, searcher, server, cli. `SearchResult` dataclass defined in searcher, used in server. `handle_search/list/reindex` functions defined in server.py, imported in cli.py and tests.
