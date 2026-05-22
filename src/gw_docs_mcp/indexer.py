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
        """Index all PDFs in pdf_dir. Returns {filename: chunk_count}. Implemented in Task 4."""
        raise NotImplementedError
