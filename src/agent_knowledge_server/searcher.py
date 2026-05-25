from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from agent_knowledge_server.config import AgentKnowledgeConfig
from agent_knowledge_server.registry import SourceRecord, SourceRegistry


@dataclass
class SearchResult:
    text: str
    source_id: str
    title: str
    original: str
    page: int
    score: float


class Searcher:
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

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        k = top_k if top_k is not None else self.cfg.search.top_k
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        model = self._get_model()
        query_vec = model.encode([query], show_progress_bar=False)[0].tolist()
        raw = collection.query(query_embeddings=[query_vec], n_results=min(k, collection.count()))
        results: list[SearchResult] = []
        for text, meta, distance in zip(raw["documents"][0], raw["metadatas"][0], raw["distances"][0]):
            results.append(
                SearchResult(
                    text=text,
                    source_id=meta["source_id"],
                    title=meta["source_title"],
                    original=meta["original"],
                    page=int(meta.get("page", 0)),
                    score=round(1.0 - distance, 4),
                )
            )
        return results

    def list_sources(self) -> list[SourceRecord]:
        return self.registry.list_sources()

    def find_sources(self, target: str) -> list[SourceRecord]:
        needle = target.strip().lower()
        if not needle:
            return []
        exact_id = []
        exact_label = []
        exact_original = []
        fuzzy = []
        for source in self.registry.list_sources():
            label = (source.source_label or source.title or source.original).lower()
            title = (source.title or "").lower()
            original = source.original.lower()
            if source.source_id == target:
                exact_id.append(source)
            elif label == needle:
                exact_label.append(source)
            elif original == needle:
                exact_original.append(source)
            elif needle in label or needle in title or needle in original:
                fuzzy.append(source)
        if exact_id:
            return exact_id
        if exact_label:
            return exact_label
        if exact_original:
            return exact_original
        return fuzzy

    def list_documents(self) -> list[dict]:
        documents = []
        for source in self.registry.list_sources():
            for document in source.documents:
                documents.append(
                    {
                        "source_id": source.source_id,
                        "source_label": source.source_label or source.title or source.original,
                        "source_title": source.title or source.original,
                        "original": source.original,
                        "document_id": document.document_id,
                        "title": document.title,
                        "content_type": document.content_type,
                    }
                )
        return documents
