from __future__ import annotations
from sentence_transformers import SentenceTransformer  # noqa: F401 — imported for monkeypatching in tests

from gw_docs_mcp.config import GwDocsConfig


class Searcher:
    """Stub — implemented in Task 5."""

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
