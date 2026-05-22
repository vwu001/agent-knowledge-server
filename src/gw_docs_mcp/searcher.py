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
