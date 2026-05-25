from typer.testing import CliRunner

from local_knowledge_mcp.cli import app

runner = CliRunner()


def test_add_file_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: temp_config)
    result = runner.invoke(app, ["add", "--file", str(sample_pdf)])
    assert result.exit_code == 0
    assert "indexed" in result.output.lower()


def test_list_sources_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: temp_config)
    runner.invoke(app, ["add", "--file", str(sample_pdf)])
    result = runner.invoke(app, ["list-sources"])
    assert result.exit_code == 0
    assert sample_pdf.name in result.output


def test_search_command(sample_pdf, mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: temp_config)
    runner.invoke(app, ["add", "--file", str(sample_pdf)])
    result = runner.invoke(app, ["search", "database queries"])
    assert result.exit_code == 0
    assert "Query.make" in result.output


def test_add_text_command(mock_embedder, temp_config, monkeypatch):
    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: temp_config)
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
    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: temp_config)
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
    from local_knowledge_mcp import installer

    monkeypatch.setattr("local_knowledge_mcp.cli.load_config", lambda: None)
    monkeypatch.setattr(installer, "detect_targets", lambda codex, claude: ["codex", "claude"])
    monkeypatch.setattr(
        installer,
        "default_skill_dirs",
        lambda: {"codex": tmp_path / "codex-skills", "claude": tmp_path / "claude-skills"},
    )
    monkeypatch.setattr(installer, "register_claude_mcp", lambda: (True, "registered"))
    monkeypatch.setattr(installer, "codex_mcp_guidance", lambda: "Run codex MCP registration manually.")

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    assert (tmp_path / "codex-skills" / "local-knowledge-mcp" / "SKILL.md").exists()
    assert (tmp_path / "claude-skills" / "local-knowledge-mcp" / "SKILL.md").exists()
    assert "registered" in result.output.lower()
