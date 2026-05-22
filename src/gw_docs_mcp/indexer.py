from __future__ import annotations
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

from gw_docs_mcp.config import GwDocsConfig


def extract_pages(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract text from each page of a PDF. Returns list of {text, page, source}."""
    pages = []
    with fitz.open(str(pdf_path)) as doc:
        for page_num in range(len(doc)):
            text = doc[page_num].get_text().strip()
            if text:
                pages.append({
                    "text": text,
                    "page": page_num,
                    "source": pdf_path.name,
                })
    return pages


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-based chunks."""
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
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
                vecs = model.encode(chunks, show_progress_bar=False)
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
