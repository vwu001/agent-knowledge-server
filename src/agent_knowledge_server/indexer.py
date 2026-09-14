from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
import fcntl
from hashlib import sha1
from pathlib import Path
import shutil
from typing import TYPE_CHECKING

import chromadb
from chromadb.config import Settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from agent_knowledge_server.config import AgentKnowledgeConfig
from agent_knowledge_server.loaders import NormalizedDocument, load_file_documents, load_url_documents
from agent_knowledge_server.registry import DocumentSummary, SourceRecord, SourceRegistry
from agent_knowledge_server.validation import (
    DEFAULT_UNKNOWN_VERSION,
    EmptyExtractionError,
    assess_extraction,
    detect_version,
    version_from_filename,
)


def _sentence_transformer_cls() -> type[SentenceTransformer]:
    """Import SentenceTransformer on first use.

    sentence_transformers pulls in torch/transformers, which costs ~4s warm and far
    more with a cold page cache. At module scope that cost lands on every MCP server
    start, before the stdio handshake completes, and trips the client's connect
    timeout. Tests patch this function to avoid loading the real model.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer


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


def file_fingerprint(path: Path) -> str:
    """Hash of a file's bytes, used by sync to detect changes without re-parsing."""
    digest = sha1()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Indexer:
    def __init__(self, cfg: AgentKnowledgeConfig) -> None:
        self.cfg = cfg
        self.registry = SourceRegistry(cfg)
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = _sentence_transformer_cls()(
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

    def _lock_path(self) -> Path:
        return self.cfg.paths.data_dir / ".write.lock"

    @contextmanager
    def _write_lock(self):
        self.cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._lock_path(), "a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

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
                        "version": meta.get("version", "") or record.version or "",
                    }
                )

        if ids:
            collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

        record.version = meta.get("version", "") or record.version
        record.content_type = meta.get("content_type", record.content_type)
        record.title = meta.get("title", record.title) or record.original
        record.source_label = meta.get("source_label", record.source_label) or record.title
        record.status = "indexed"
        record.last_indexed_at = datetime.now(UTC).isoformat()
        record.updated_at = record.last_indexed_at
        record.error = ""
        record.fingerprint = sha1("".join(doc.content for doc in documents).encode("utf-8")).hexdigest()
        if "file_fingerprint" in meta:
            record.file_fingerprint = meta["file_fingerprint"]
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

    def _add_file_source_unlocked(
        self,
        path: Path,
        source_label: str | None = None,
        force: bool = False,
    ) -> SourceRecord:
        path = Path(path).expanduser()
        if path.is_dir():
            raise ValueError(f"Folder paths are not supported: {path}")
        record = self.registry.upsert_file(path, source_label=source_label)
        try:
            documents, meta = load_file_documents(path)
            self._guard_extraction(record, documents, origin=str(path), force=force, min_chars=0)
            meta = dict(meta)
            # Prefer the release the document stamps on itself, then a codename in
            # the filename for guides that never print one, then the assumed default.
            meta.setdefault(
                "version",
                detect_version(
                    documents,
                    fallback=version_from_filename(path.name) or DEFAULT_UNKNOWN_VERSION,
                ),
            )
            meta["file_fingerprint"] = file_fingerprint(path)
            if source_label:
                meta["source_label"] = source_label
            return self._index_documents(record, documents, meta)
        except Exception as exc:
            record.status = "empty" if isinstance(exc, EmptyExtractionError) else "failed"
            record.error = str(exc)
            self.registry.save(record)
            raise

    def _guard_extraction(
        self,
        record: SourceRecord,
        documents,
        origin: str,
        force: bool,
        min_chars: int | None = None,
    ) -> None:
        """Refuse to record an empty extraction as a successful index."""
        if force:
            return
        kwargs = {} if min_chars is None else {"min_chars": min_chars}
        problem = assess_extraction(documents, origin=origin, **kwargs)
        if problem:
            raise EmptyExtractionError(problem)

    def add_file_source(
        self,
        path: Path,
        source_label: str | None = None,
        force: bool = False,
    ) -> SourceRecord:
        with self._write_lock():
            return self._add_file_source_unlocked(path, source_label=source_label, force=force)

    def _import_pdf_folder_unlocked(self, folder: Path, pattern: str = "*.pdf") -> list[SourceRecord]:
        folder = Path(folder).expanduser()
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder}")

        imported: list[SourceRecord] = []
        for pdf_path in sorted(folder.glob(pattern)):
            if pdf_path.is_file():
                imported.append(self._add_file_source_unlocked(pdf_path))
        return imported

    def import_pdf_folder(self, folder: Path, pattern: str = "*.pdf") -> list[SourceRecord]:
        with self._write_lock():
            return self._import_pdf_folder_unlocked(folder, pattern=pattern)

    def _add_url_source_unlocked(
        self,
        url: str,
        source_label: str | None = None,
        force: bool = False,
    ) -> SourceRecord:
        record = self.registry.upsert_url(url, source_label=source_label)
        try:
            documents, meta = load_url_documents(url, self._source_dir(record.source_id))
            self._guard_extraction(record, documents, origin=url, force=force)
            meta = dict(meta)
            meta.setdefault("version", detect_version(documents))
            if source_label:
                meta["source_label"] = source_label
            return self._index_documents(record, documents, meta)
        except Exception as exc:
            record.status = "empty" if isinstance(exc, EmptyExtractionError) else "failed"
            record.error = str(exc)
            self.registry.save(record)
            raise

    def add_url_source(
        self,
        url: str,
        source_label: str | None = None,
        force: bool = False,
    ) -> SourceRecord:
        with self._write_lock():
            return self._add_url_source_unlocked(url, source_label=source_label, force=force)

    def _add_text_source_unlocked(
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

    def add_text_source(
        self,
        content: str,
        source_label: str,
        title: str | None = None,
        source_kind: str | None = None,
        original_ref: str | None = None,
        notes: str | None = None,
    ) -> SourceRecord:
        with self._write_lock():
            return self._add_text_source_unlocked(
                content=content,
                source_label=source_label,
                title=title,
                source_kind=source_kind,
                original_ref=original_ref,
                notes=notes,
            )

    def sync_folder(
        self,
        folder: Path,
        pattern: str = "*.pdf",
        reindex_unknown: bool = False,
    ) -> dict[str, list[str]]:
        """Reconcile a directory against the index.

        Returns lists keyed by outcome:
          added      - file present on disk, not in the registry; now indexed
          updated    - file bytes changed since last index; re-indexed
          unchanged  - byte fingerprint matches the registry
          backfilled - indexed before fingerprints existed; fingerprint recorded,
                       content left alone (pass reindex_unknown to re-index instead)
          missing    - registry has a file source whose path no longer exists
          failed     - indexing raised; see the registry entry's error
        """
        folder = Path(folder).expanduser()
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {folder}")

        report: dict[str, list[str]] = {
            "added": [],
            "updated": [],
            "unchanged": [],
            "backfilled": [],
            "missing": [],
            "failed": [],
        }

        with self._write_lock():
            on_disk = sorted(p for p in folder.glob(pattern) if p.is_file())
            seen_ids: set[str] = set()

            for path in on_disk:
                resolved = str(path.expanduser().resolve())
                source_id = self.registry._source_id("file", resolved)
                seen_ids.add(source_id)
                existing = self.registry.get(source_id)
                name = path.name
                try:
                    if existing is None or existing.status != "indexed":
                        self._add_file_source_unlocked(path)
                        report["added"].append(name)
                        continue
                    current = file_fingerprint(path)
                    if not existing.file_fingerprint:
                        # Indexed before byte fingerprints were recorded. Record one
                        # rather than re-parsing an unchanged corpus.
                        if reindex_unknown:
                            self._add_file_source_unlocked(path)
                            report["updated"].append(name)
                        else:
                            existing.file_fingerprint = current
                            self.registry.save(existing)
                            report["backfilled"].append(name)
                    elif existing.file_fingerprint != current:
                        self._add_file_source_unlocked(path)
                        report["updated"].append(name)
                    else:
                        report["unchanged"].append(name)
                except Exception as exc:  # keep going; the registry records the error
                    report["failed"].append(f"{name}: {exc}")

            for record in self.registry.list_sources():
                if record.kind != "file" or record.source_id in seen_ids:
                    continue
                if not Path(record.original).exists():
                    report["missing"].append(f"{record.source_label or record.title} ({record.source_id})")

        return report

    def refresh_source(self, source_id: str) -> SourceRecord:
        with self._write_lock():
            record = self.registry.get(source_id)
            if record is None:
                raise KeyError(f"Unknown source_id: {source_id}")
            if record.kind == "file":
                return self._add_file_source_unlocked(Path(record.original))
            return self._add_url_source_unlocked(record.original)

    def forget_source(self, source_id: str) -> None:
        with self._write_lock():
            self._delete_source_chunks(source_id)
            source_dir = self._source_dir(source_id)
            if source_dir.exists():
                shutil.rmtree(source_dir)
            self.registry.delete(source_id)
