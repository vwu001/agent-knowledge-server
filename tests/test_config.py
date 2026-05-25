from local_knowledge_mcp.config import load_config, save_config


def test_defaults_when_no_file(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg.search.top_k == 5
    assert cfg.search.chunk_size == 500
    assert cfg.search.chunk_overlap == 50
    assert cfg.model.name == "all-MiniLM-L6-v2"
    assert cfg.paths.config_path == tmp_path / "nonexistent.toml"
    assert "local-knowledge-mcp" in str(cfg.paths.data_dir)


def test_round_trip_preserves_overrides(tmp_path):
    config_path = tmp_path / "config.toml"
    cfg = load_config(config_path)
    cfg.model.name = "custom-model"
    save_config(cfg, config_path)
    reloaded = load_config(config_path)
    assert reloaded.model.name == "custom-model"


def test_save_creates_parent_directories(tmp_path):
    config_path = tmp_path / "nested" / "config.toml"
    cfg = load_config(config_path)
    save_config(cfg, config_path)
    assert config_path.exists()
