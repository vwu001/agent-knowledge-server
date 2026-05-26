from typer.testing import CliRunner

from agent_knowledge_server.cli import app

runner = CliRunner()


def test_add_file_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["add", "--file", str(sample_pdf)])
    assert result.exit_code == 0
    assert "indexed" in result.output.lower()


def test_list_sources_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)
    runner.invoke(app, ["add", "--file", str(sample_pdf)])
    result = runner.invoke(app, ["list-sources"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_search_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)
    runner.invoke(app, ["add", "--file", str(sample_pdf)])
    result = runner.invoke(app, ["search", "database queries"])
    assert result.exit_code == 0
    assert "Query.make" in result.output


def test_add_text_command(mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)
    result = runner.invoke(
        app,
        [
            "add-text",
            "--source-label",
            "repo notes",
            "--content",
            "Local setup notes for this repository.",
            "--title",
            "Repo Notes",
        ],
    )
    assert result.exit_code == 0
    assert "indexed" in result.output.lower()


def test_forget_by_target_command(mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)
    runner.invoke(
        app,
        [
            "add-text",
            "--source-label",
            "bad note",
            "--content",
            "This note is wrong.",
            "--title",
            "Bad Note",
        ],
    )
    result = runner.invoke(app, ["forget", "--target", "bad note", "--yes"])
    assert result.exit_code == 0
    assert "forgot" in result.output.lower()


def test_install_command_writes_skill_files(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: None)
    monkeypatch.setattr(installer, "detect_targets", lambda codex, claude: ["codex", "claude"])
    monkeypatch.setattr(
        installer,
        "default_skill_dirs",
        lambda: {"codex": tmp_path / "codex-skills", "claude": tmp_path / "claude-skills"},
    )
    monkeypatch.setattr(installer, "default_codex_config_path", lambda: tmp_path / "codex-config.toml")
    monkeypatch.setattr(installer, "default_claude_settings_path", lambda: tmp_path / "claude-settings.json")
    monkeypatch.setattr(installer, "register_claude_mcp", lambda: (True, "registered"))

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    assert (tmp_path / "codex-skills" / "agent-knowledge-server" / "SKILL.md").exists()
    assert (tmp_path / "claude-skills" / "agent-knowledge-server" / "SKILL.md").exists()
    assert (tmp_path / "codex-config.toml").exists()
    assert (tmp_path / "claude-settings.json").exists()
    assert "registered" in result.output.lower()


def test_import_pdfs_command(tmp_path, sample_pdf, mock_embedder, temp_config, monkeypatch):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    (folder / "GuideA.pdf").write_bytes(sample_pdf.read_bytes())
    (folder / "GuideB.pdf").write_bytes(sample_pdf.read_bytes())
    monkeypatch.setattr("agent_knowledge_server.cli.load_config", lambda: temp_config)

    result = runner.invoke(app, ["import-pdfs", "--dir", str(folder)])

    assert result.exit_code == 0
    assert "Imported 2 PDF source(s)" in result.output
