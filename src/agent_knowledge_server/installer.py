from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


SKILL_NAME = "agent-knowledge-server"


def build_skill_text() -> str:
    return """---
name: agent-knowledge-server
description: Use when a user wants to save useful content to agent knowledge, search saved knowledge, or forget incorrect saved knowledge
---

# agent-knowledge-server

Use this skill when the user wants to interact with the agent knowledge MCP.

## Save Knowledge

- If the user wants to save useful knowledge from accessible content, normalize the content first.
- Prefer `add_text_source` for LLM-derived content.
- Prefer `add_source` for a single explicit file path or URL.
- Include a human-readable `source_label` whenever possible.

## Search Knowledge

- Use `search_knowledge` to find previously saved information.
- Use `list_sources` or `list_documents` when the user wants to inspect what is stored.

## Remove Wrong Knowledge

- If the user says content is wrong, stale, or should be removed, use `forget_source`.
- Prefer a natural target or label when possible, not only source ids.
"""


def default_skill_dirs() -> dict[str, Path]:
    return {
        "codex": Path.home() / ".codex" / "skills",
        "claude": Path.home() / ".claude" / "skills",
    }


def install_global_skill(base_dir: Path, skill_name: str = SKILL_NAME) -> Path:
    skill_dir = base_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(build_skill_text(), encoding="utf-8")
    return skill_path


def detect_targets(codex: bool, claude: bool) -> list[str]:
    if codex or claude:
        targets = []
        if codex:
            targets.append("codex")
        if claude:
            targets.append("claude")
        return targets
    return ["codex", "claude"]


def register_claude_mcp() -> tuple[bool, str]:
    if shutil.which("claude") is None:
        return False, "Claude CLI not found. Install it, then run: claude mcp add --scope user agent-knowledge -- agent-knowledge-server serve"
    try:
        proc = subprocess.run(
            ["claude", "mcp", "add", "--scope", "user", "agent-knowledge", "--", "agent-knowledge-server", "serve"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, f"Claude MCP registration failed: {exc}"
    if proc.returncode == 0:
        return True, proc.stdout.strip() or "Claude MCP registered."
    message = proc.stderr.strip() or proc.stdout.strip() or "Claude MCP registration failed."
    return False, message


def codex_mcp_guidance() -> str:
    return "Codex MCP registration may require local environment-specific setup. Ensure the agent-knowledge MCP server is registered in your Codex environment and restart the session."


def install_everything(
    *,
    install_skill: bool,
    install_mcp: bool,
    codex: bool,
    claude: bool,
) -> list[str]:
    messages: list[str] = []
    targets = detect_targets(codex, claude)

    if install_skill:
        dirs = default_skill_dirs()
        for target in targets:
            skill_path = install_global_skill(dirs[target], SKILL_NAME)
            messages.append(f"Installed {target} skill: {skill_path}")

    if install_mcp:
        if "claude" in targets:
            ok, message = register_claude_mcp()
            prefix = "Claude MCP" if ok else "Claude MCP notice"
            messages.append(f"{prefix}: {message}")
        if "codex" in targets:
            messages.append(f"Codex MCP notice: {codex_mcp_guidance()}")

    messages.append("Start a new assistant session after installation.")
    return messages
