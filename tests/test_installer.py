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


def test_sync_folder_is_pre_approved():
    """sync_folder is the tool org users need for OneDrive-synced doc folders.

    Omitting it means every sync prompts for approval.
    """
    from agent_knowledge_server.installer import CLAUDE_ALLOWED_TOOLS

    assert "mcp__agent-knowledge__sync_folder" in CLAUDE_ALLOWED_TOOLS


def test_allowed_tools_cover_every_mcp_tool():
    from agent_knowledge_server.installer import CLAUDE_ALLOWED_TOOLS
    from agent_knowledge_server.tools import TOOL_NAMES

    exported = {f"mcp__agent-knowledge__{name}" for name in TOOL_NAMES}
    assert exported == set(CLAUDE_ALLOWED_TOOLS)


def test_build_skill_text_matches_packaged_skill_file():
    """Guards against the skill text drifting from the canonical SKILL.md."""
    from agent_knowledge_server.installer import bundled_skill_path

    assert build_skill_text() == bundled_skill_path().read_text(encoding="utf-8")


def test_build_skill_text_documents_org_doc_ingestion():
    skill_text = build_skill_text()
    assert "sync_folder" in skill_text
    assert "OneDrive" in skill_text
    assert "CloudStorage" in skill_text


def test_build_skill_text_documents_dev_workflow():
    skill_text = build_skill_text()
    assert "add_text_source_from_context" in skill_text
    assert "source_label" in skill_text


# --- MCP command resolution -------------------------------------------------
#
# A venv install puts the console script in <venv>/bin, which is NOT on PATH
# unless the venv is activated. Agents launch the MCP server with the user's
# PATH, so a bare "agent-knowledge-server" silently fails to connect there.


def _fake_script(tmp_path, name="agent-knowledge-server"):
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    script = bindir / name
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_server_command_prefers_bare_name_when_path_already_resolves(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    script = _fake_script(tmp_path)
    monkeypatch.setattr(installer.sys, "executable", str(script.parent / "python"))
    monkeypatch.setattr(installer.shutil, "which", lambda name: str(script))

    assert installer.server_command() == "agent-knowledge-server"


def test_server_command_uses_absolute_path_for_unactivated_venv(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    script = _fake_script(tmp_path)
    monkeypatch.setattr(installer.sys, "executable", str(script.parent / "python"))
    # PATH resolves to some *other* install, or nothing at all
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/local/bin/agent-knowledge-server")

    assert installer.server_command() == str(script)


def test_server_command_falls_back_to_bare_name_when_nothing_found(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    monkeypatch.setattr(installer.sys, "executable", str(tmp_path / "nowhere" / "python"))
    monkeypatch.setattr(installer.shutil, "which", lambda name: None)

    assert installer.server_command() == "agent-knowledge-server"


def test_codex_block_uses_resolved_command(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    monkeypatch.setattr(installer, "server_command", lambda: "/opt/venv/bin/agent-knowledge-server")
    configure_codex_mcp(tmp_path / "config.toml")

    text = (tmp_path / "config.toml").read_text()
    assert 'command = "/opt/venv/bin/agent-knowledge-server"' in text


def test_install_warns_when_command_is_not_on_path(tmp_path, monkeypatch):
    from agent_knowledge_server import installer

    monkeypatch.setattr(installer, "detect_targets", lambda codex, claude: ["codex"])
    monkeypatch.setattr(installer, "default_codex_config_path", lambda: tmp_path / "codex-config.toml")
    monkeypatch.setattr(installer, "server_command", lambda: "/opt/venv/bin/agent-knowledge-server")

    messages = install_everything(install_skill=False, install_mcp=True, codex=True, claude=False)

    joined = "\n".join(messages)
    assert "not on your PATH" in joined
    assert "/opt/venv/bin/agent-knowledge-server" in joined
