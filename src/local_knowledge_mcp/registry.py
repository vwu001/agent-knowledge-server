from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha1
import json
from pathlib import Path

from local_knowledge_mcp.config import LocalKnowledgeConfig


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DocumentSummary:
    document_id: str
    title: str
    content_type: str
    location: str = ""


@dataclass
class SourceRecord:
    source_id: str
    kind: str
    original: str
    source_label: str = ""
    content_type: str = ""
    title: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    last_indexed_at: str = ""
    fingerprint: str = ""
    error: str = ""
    documents: list[DocumentSummary] = field(default_factory=list)


class SourceRegistry:
    def __init__(self, cfg: LocalKnowledgeConfig) -> None:
        self.cfg = cfg
        self.cfg.paths.sources_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.paths.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, SourceRecord]:
        path = self.cfg.paths.registry_path
        if not path.exists():
            return {}
        raw = json.loads(path.read_text() or "{}")
        items = {}
        for source_id, data in raw.items():
            documents = [DocumentSummary(**doc) for doc in data.get("documents", [])]
            data = {k: v for k, v in data.items() if k != "documents"}
            items[source_id] = SourceRecord(**data, documents=documents)
        return items

    def _save_all(self, items: dict[str, SourceRecord]) -> None:
        payload = {}
        for source_id, record in items.items():
            payload[source_id] = asdict(record)
        self.cfg.paths.registry_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def _source_id(self, kind: str, original: str) -> str:
        return f"{kind}-{sha1(original.encode('utf-8')).hexdigest()[:12]}"

    def list_sources(self) -> list[SourceRecord]:
        return sorted(self._load_all().values(), key=lambda item: item.updated_at, reverse=True)

    def get(self, source_id: str) -> SourceRecord | None:
        return self._load_all().get(source_id)

    def save(self, record: SourceRecord) -> SourceRecord:
        items = self._load_all()
        record.updated_at = _utc_now()
        items[record.source_id] = record
        self._save_all(items)
        return record

    def upsert_file(self, path: Path) -> SourceRecord:
        original = str(path.expanduser().resolve())
        source_id = self._source_id("file", original)
        existing = self.get(source_id)
        if existing is not None:
            existing.original = original
            existing.updated_at = _utc_now()
            return self.save(existing)
        return self.save(SourceRecord(source_id=source_id, kind="file", original=original))

    def upsert_url(self, url: str) -> SourceRecord:
        source_id = self._source_id("url", url)
        existing = self.get(source_id)
        if existing is not None:
            existing.original = url
            existing.updated_at = _utc_now()
            return self.save(existing)
        return self.save(SourceRecord(source_id=source_id, kind="url", original=url))

    def upsert_text(self, source_label: str, original_ref: str | None = None) -> SourceRecord:
        original = original_ref or source_label
        source_id = self._source_id("text", original)
        existing = self.get(source_id)
        if existing is not None:
            existing.original = original
            existing.source_label = source_label
            existing.updated_at = _utc_now()
            return self.save(existing)
        return self.save(
            SourceRecord(
                source_id=source_id,
                kind="text",
                original=original,
                source_label=source_label,
            )
        )

    def delete(self, source_id: str) -> None:
        items = self._load_all()
        items.pop(source_id, None)
        self._save_all(items)
