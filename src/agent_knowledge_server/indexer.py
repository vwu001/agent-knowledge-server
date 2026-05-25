from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
import shutil

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from agent_knowledge_server.config import AgentKnowledgeConfig
from agent_knowledge_server.loaders import NormalizedDocument, load_file_documents, load_url_documents
from agent_knowledge_server.registry import DocumentSummary, SourceRecord, SourceRegistry


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
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


class Indexer:
    def __init__(self, cfg: AgentKnowledgeConfig) -> None:
        self.cfg = cfg
        self.registry = SourceRegistry(cfg)
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
            path=str(self.cfg.paths.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        return client.get_or_create_collection("local_knowledge")

    def _delete_source_chunks(self, source_id: str) -> None:
        collection = self._get_collection()
        try:
            collection.delete(where={"source_id": source_id})
        except Exception:
            pass

    def _source_dir(self, source_id: str) -> Path:
        return self.cfg.paths.sources_dir / source_id

    def _index_documents(self, record: SourceRecord, documents: list[NormalizedDocument], meta: dict) -> SourceRecord:
        collection = self._get_collection()
        self._delete_source_chunks(record.source_id)
        model = self._get_model()

        ids: list[str] = []
        embeddings: list[list[float]] = []
        chunks: list[str] = []
        metadatas: list[dict] = []

        for document in documents:
            doc_chunks = chunk_text(document.content, self.cfg.search.chunk_size, self.cfg.search.chunk_overlap)
            vecs = model.encode(doc_chunks, show_progress_bar=False)
            for idx, (chunk, vec) in enumerate(zip(doc_chunks, vecs)):
                chunk_id = f"{record.source_id}::{document.document_id}::c{idx}"
                ids.append(chunk_id)
                embeddings.append(vec.tolist())
                chunks.append(chunk)
                metadatas.append(
                    {
                        "source_id": record.source_id,
                        "document_id": document.document_id,
                        "source_title": meta.get("title") or record.title or record.original,
                        "source_kind": record.kind,
                        "content_type": meta.get("content_type", document.content_type),
                        "original": record.original,
                        "title": document.title,
                        "page": document.metadata.get("page", 0),
                        "section_path": document.metadata.get("section_path", ""),
                    }
                )

        if ids:
            collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

        record.content_type = meta.get("content_type", record.content_type)
        record.title = meta.get("title", record.title) or record.original
        record.source_label = meta.get("source_label", record.source_label) or record.title
        record.status = "indexed"
        record.last_indexed_at = datetime.now(UTC).isoformat()
        record.updated_at = record.last_indexed_at
        record.error = ""
        record.fingerprint = sha1("".join(doc.content for doc in documents).encode("utf-8")).hexdigest()
        record.documents = [
            DocumentSummary(
                document_id=doc.document_id,
                title=doc.title,
                content_type=doc.content_type,
                location=str(doc.metadata.get("page", "")),
            )
            for doc in documents
        ]
        return self.registry.save(record)

    def add_file_source(self, path: Path) -> SourceRecord:
        path = Path(path).expanduser()
        if path.is_dir():
            raise ValueError(f"Folder paths are not supported: {path}")
        record = self.registry.upsert_file(path)
        try:
            documents, meta = load_file_documents(path)
            return self._index_documents(record, documents, meta)
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            self.registry.save(record)
            raise

    def import_pdf_folder(self, folder: Path, pattern: str = "*.pdf") -> list[SourceRecord]:
        folder = Path(folder).expanduser()
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder}")

        imported: list[SourceRecord] = []
        for pdf_path in sorted(folder.glob(pattern)):
            if pdf_path.is_file():
                imported.append(self.add_file_source(pdf_path))
        return imported

    def add_url_source(self, url: str) -> SourceRecord:
        record = self.registry.upsert_url(url)
        try:
            documents, meta = load_url_documents(url, self._source_dir(record.source_id))
            return self._index_documents(record, documents, meta)
        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            self.registry.save(record)
            raise

    def add_text_source(
        self,
        content: str,
        source_label: str,
        title: str | None = None,
        source_kind: str | None = None,
        original_ref: str | None = None,
        notes: str | None = None,
    ) -> SourceRecord:
        record = self.registry.upsert_text(source_label, original_ref=original_ref)
        source_dir = self._source_dir(record.source_id)
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "content.txt").write_text(content, encoding="utf-8")
        if notes:
            (source_dir / "notes.txt").write_text(notes, encoding="utf-8")

        document = NormalizedDocument(
            document_id=f"{record.source_id}::root",
            title=title or source_label,
            content=content,
            content_type="text",
            metadata={"section_path": "", "source_kind": source_kind or "llm_text"},
        )
        meta = {
            "content_type": "text",
            "title": title or source_label,
            "source_label": source_label,
        }
        return self._index_documents(record, [document], meta)

    def refresh_source(self, source_id: str) -> SourceRecord:
        record = self.registry.get(source_id)
        if record is None:
            raise KeyError(f"Unknown source_id: {source_id}")
        if record.kind == "file":
            return self.add_file_source(Path(record.original))
        return self.add_url_source(record.original)

    def forget_source(self, source_id: str) -> None:
        self._delete_source_chunks(source_id)
        source_dir = self._source_dir(source_id)
        if source_dir.exists():
            shutil.rmtree(source_dir)
        self.registry.delete(source_id)
