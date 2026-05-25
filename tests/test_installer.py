from local_knowledge_mcp.installer import build_skill_text, install_global_skill


def test_build_skill_text_mentions_core_tools():
    skill_text = build_skill_text()
    assert "add_text_source" in skill_text
    assert "search_knowledge" in skill_text
    assert "forget_source" in skill_text


def test_install_global_skill_writes_skill_md(tmp_path):
    skill_dir = tmp_path / "skills"
    installed = install_global_skill(skill_dir, "local-knowledge-mcp")

    assert installed.exists()
    assert installed.name == "SKILL.md"
    assert "local-knowledge-mcp" in installed.read_text()
