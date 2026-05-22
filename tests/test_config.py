from pathlib import Path
import pytest
from gw_docs_mcp.config import GwDocsConfig, load_config, save_config, DEFAULT_CONFIG_PATH


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", tmp_path / "nonexistent.toml")
    cfg = load_config()
    assert cfg.search.top_k == 5
    assert cfg.search.chunk_size == 500
    assert cfg.search.chunk_overlap == 50
    assert cfg.model.name == "all-MiniLM-L6-v2"
    assert cfg.chroma.collection == "gw_docs"


def test_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    cfg.docs.pdf_dir = "/some/pdf/dir"
    save_config(cfg)
    reloaded = load_config()
    assert reloaded.docs.pdf_dir == "/some/pdf/dir"


def test_tilde_expansion(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    cfg.docs.pdf_dir = "~/my-pdfs"
    save_config(cfg)
    reloaded = load_config()
    assert reloaded.docs.pdf_dir == "~/my-pdfs"


def test_chroma_dir_is_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    cfg = load_config()
    assert isinstance(cfg.chroma.persist_dir, str)
