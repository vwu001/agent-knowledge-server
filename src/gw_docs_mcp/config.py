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
    cache_dir: str = field(default_factory=lambda: str(Path.home() / ".gw-docs-mcp" / "models"))


@dataclass
class ChromaConfig:
    persist_dir: str = field(default_factory=lambda: str(Path.home() / ".gw-docs-mcp" / "chroma"))
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
