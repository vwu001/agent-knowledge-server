import json

from agent_knowledge_server.installer import (
    build_skill_text,
    configure_claude_permissions,
    configure_codex_mcp,
    install_everything,
    install_global_skill,
)


def test_build_skill_text_mentions_core_tools():
    skill_text = build_skill_text()
    assert "add_text_source" in skill_text
    assert "search_knowledge" in skill_text
    assert "forget_source" in skill_text
    assert "import_pdf_folder" in skill_text
    assert "agent-knowledge-server install" in skill_text
    assert "~/.codex/config.toml" in skill_text
    assert "default_tools_approval_mode = \"approve\"" in skill_text
    assert "~/.claude/settings.json" in skill_text
    assert "mcp__agent-knowledge__search_knowledge" in skill_text


def test_install_global_skill_writes_skill_md(tmp_path):
    skill_dir = tmp_path / "skills"
    installed = install_global_skill(skill_dir, "agent-knowledge-server")

    assert installed.exists()
    assert installed.name == "SKILL.md"
    assert "agent-knowledge-server" in installed.read_text()


def test_configure_codex_mcp_writes_server_block(tmp_path):
    config_path = tmp_path / "config.toml"

    message = configure_codex_mcp(config_path)

    text = config_path.read_text()
    assert "configured" in message.lower()
    assert '[mcp_servers.agent-knowledge]' in text
    assert 'command = "agent-knowledge-server"' in text
    assert 'args = ["serve"]' in text
    assert 'default_tools_approval_mode = "approve"' in text


def test_configure_codex_mcp_updates_existing_server_block(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[mcp_servers.agent-knowledge]\n'
        'command = "old-command"\n'
        'args = ["old"]\n'
        '\n'
        '[projects."/tmp/example"]\n'
        'trust_level = "trusted"\n',
        encoding="utf-8",
    )

    configure_codex_mcp(config_path)

    text = config_path.read_text()
    assert text.count("[mcp_servers.agent-knowledge]") == 1
    assert 'command = "agent-knowledge-server"' in text
    assert 'args = ["serve"]' in text
    assert 'default_tools_approval_mode = "approve"' in text
    assert '[projects."/tmp/example"]' in text


def test_configure_claude_permissions_adds_mcp_tools(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"permissions": {"allow": ["Read"]}}, indent=2), encoding="utf-8")

    message = configure_claude_permissions(settings_path)

    payload = json.loads(settings_path.read_text())
    allow = payload["permissions"]["allow"]
    assert "updated" in message.lower()
    assert "Read" in allow
    assert "mcp__agent-knowledge__search_knowledge" in allow
    assert "mcp__agent-knowledge__forget_source" in allow


def test_configure_claude_permissions_is_idempotent(tmp_path):
    settings_path = tmp_path / "settings.json"

    configure_claude_permissions(settings_path)
    configure_claude_permissions(settings_path)

    payload = json.loads(settings_path.read_text())
    allow = payload["permissions"]["allow"]
    assert allow.count("mcp__agent-knowledge__search_knowledge") == 1
    assert allow.count("mcp__agent-knowledge__add_source") == 1


def test_install_everything_configures_targets(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    monkeypatch.setattr(installer, "detect_targets", lambda codex, claude: ["codex", "claude"])
    monkeypatch.setattr(
        installer,
        "default_skill_dirs",
        lambda: {"codex": tmp_path / "codex-skills", "claude": tmp_path / "claude-skills"},
    )
    monkeypatch.setattr(installer, "default_codex_config_path", lambda: tmp_path / "codex-config.toml")
    monkeypatch.setattr(installer, "default_claude_settings_path", lambda: tmp_path / "claude-settings.json")
    monkeypatch.setattr(installer, "register_claude_mcp", lambda: (True, "registered"))

    messages = install_everything(
        install_skill=True,
        install_mcp=True,
        codex=False,
        claude=False,
    )

    assert any("Installed codex skill:" in message for message in messages)
    assert any("Installed claude skill:" in message for message in messages)
    assert any("Codex MCP:" in message for message in messages)
    assert any("Claude permissions:" in message for message in messages)
    assert any("Claude MCP: registered" in message for message in messages)
