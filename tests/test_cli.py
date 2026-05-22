import shutil
from pathlib import Path
from typer.testing import CliRunner
from gw_docs_mcp.cli import app

runner = CliRunner()


def test_configure_writes_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr("gw_docs_mcp.cli.DEFAULT_CONFIG_PATH", config_path)
    result = runner.invoke(app, ["configure", "--pdf-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Saved" in result.output
    assert config_path.exists()


def test_configure_shows_saved_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr("gw_docs_mcp.config.DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr("gw_docs_mcp.cli.DEFAULT_CONFIG_PATH", config_path)
    result = runner.invoke(app, ["configure", "--pdf-dir", "/my/pdfs"])
    assert "/my/pdfs" in result.output


def test_index_command(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    temp_config.docs.pdf_dir = str(pdf_dir)

    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["index"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_index_command_with_override_dir(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["index", "--pdf-dir", str(pdf_dir)])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_status_shows_indexed_files(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    shutil.copy(sample_pdf, pdf_dir / sample_pdf.name)
    from gw_docs_mcp.indexer import Indexer
    Indexer(temp_config).index_directory(pdf_dir)
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_status_no_docs(tmp_path, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("gw_docs_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No documents" in result.output
