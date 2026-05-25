from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import tomllib

import tomli_w

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "agent-knowledge-server" / "config.toml"


@dataclass
class AppPaths:
    config_path: Path
    data_dir: Path
    sources_dir: Path
    registry_path: Path
    chroma_dir: Path
    models_dir: Path


@dataclass
class SearchConfig:
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50


@dataclass
class ModelConfig:
    name: str = "all-MiniLM-L6-v2"
    cache_dir: str = ""


@dataclass
class AgentKnowledgeConfig:
    paths: AppPaths
    search: SearchConfig = field(default_factory=SearchConfig)
    model: ModelConfig = field(default_factory=ModelConfig)


def build_default_paths(config_path: Path = DEFAULT_CONFIG_PATH) -> AppPaths:
    data_dir = Path.home() / ".local" / "share" / "agent-knowledge-server"
    return AppPaths(
        config_path=config_path,
        data_dir=data_dir,
        sources_dir=data_dir / "sources",
        registry_path=data_dir / "sources" / "registry.json",
        chroma_dir=data_dir / "chroma",
        models_dir=data_dir / "models",
    )


def _config_to_dict(cfg: AgentKnowledgeConfig) -> dict:
    return {
        "paths": {
            "config_path": str(cfg.paths.config_path),
            "data_dir": str(cfg.paths.data_dir),
            "sources_dir": str(cfg.paths.sources_dir),
            "registry_path": str(cfg.paths.registry_path),
            "chroma_dir": str(cfg.paths.chroma_dir),
            "models_dir": str(cfg.paths.models_dir),
        },
        "search": asdict(cfg.search),
        "model": asdict(cfg.model),
    }


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AgentKnowledgeConfig:
    defaults = build_default_paths(path)
    cfg = AgentKnowledgeConfig(
        paths=defaults,
        model=ModelConfig(cache_dir=str(defaults.models_dir)),
    )
    if not path.exists():
        return cfg

    with open(path, "rb") as f:
        data = tomllib.load(f)

    paths = data.get("paths", {})
    cfg.paths = AppPaths(
        config_path=Path(paths.get("config_path", path)),
        data_dir=Path(paths.get("data_dir", defaults.data_dir)),
        sources_dir=Path(paths.get("sources_dir", defaults.sources_dir)),
        registry_path=Path(paths.get("registry_path", defaults.registry_path)),
        chroma_dir=Path(paths.get("chroma_dir", defaults.chroma_dir)),
        models_dir=Path(paths.get("models_dir", defaults.models_dir)),
    )

    search = data.get("search", {})
    cfg.search = SearchConfig(
        top_k=search.get("top_k", cfg.search.top_k),
        chunk_size=search.get("chunk_size", cfg.search.chunk_size),
        chunk_overlap=search.get("chunk_overlap", cfg.search.chunk_overlap),
    )

    model = data.get("model", {})
    cfg.model = ModelConfig(
        name=model.get("name", cfg.model.name),
        cache_dir=model.get("cache_dir", str(cfg.paths.models_dir)),
    )
    return cfg


def save_config(cfg: AgentKnowledgeConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    cfg.paths.config_path = path
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg.paths.data_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.sources_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.chroma_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.models_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(_config_to_dict(cfg), f)
