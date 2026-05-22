from pathlib import Path
import pytest
from gw_docs_mcp.config import GwDocsConfig, load_config, save_config


def test_defaults_when_no_file(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.search.top_k == 5
    assert cfg.search.chunk_size == 500
    assert cfg.search.chunk_overlap == 50
    assert cfg.model.name == "all-MiniLM-L6-v2"
    assert cfg.chroma.collection == "gw_docs"


def test_round_trip(tmp_path):
    config_path = tmp_path / "config.toml"
    cfg = load_config(config_path)
    cfg.docs.pdf_dir = "/some/pdf/dir"
    save_config(cfg, config_path)
    reloaded = load_config(config_path)
    assert reloaded.docs.pdf_dir == "/some/pdf/dir"


def test_tilde_stored_verbatim(tmp_path):
    config_path = tmp_path / "config.toml"
    cfg = load_config(config_path)
    cfg.docs.pdf_dir = "~/my-pdfs"
    save_config(cfg, config_path)
    reloaded = load_config(config_path)
    assert reloaded.docs.pdf_dir == "~/my-pdfs"


def test_unknown_keys_in_toml_are_ignored(tmp_path):
    config_path = tmp_path / "config.toml"
    # Write a TOML file with an extra unknown key
    config_path.write_text('[docs]\npdf_dir = "/pdfs"\nunknown_future_key = "ignored"\n')
    cfg = load_config(config_path)
    assert cfg.docs.pdf_dir == "/pdfs"  # known key is loaded
    # No crash from the unknown key


def test_chroma_persist_dir_default_contains_expected_path(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert ".gw-docs-mcp" in cfg.chroma.persist_dir
    assert isinstance(cfg.chroma.persist_dir, str)
