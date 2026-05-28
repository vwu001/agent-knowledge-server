from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

# Path to the canonical SKILL.md bundled with the package source.
# Used when installing outside the plugin system (e.g. Codex, manual installs).
_BUNDLED_SKILL = Path(__file__).parent.parent.parent / "skills" / "agent-knowledge-server" / "SKILL.md"

SKILL_NAME = "agent-knowledge-server"
SERVER_NAME = "agent-knowledge"
CODEX_SERVER_HEADER = f"[mcp_servers.{SERVER_NAME}]"
CLAUDE_ALLOWED_TOOLS = [
    "mcp__agent-knowledge__add_source",
    "mcp__agent-knowledge__add_text_source",
    "mcp__agent-knowledge__add_text_source_from_context",
    "mcp__agent-knowledge__import_pdf_folder",
    "mcp__agent-knowledge__list_sources",
    "mcp__agent-knowledge__list_documents",
    "mcp__agent-knowledge__search_knowledge",
    "mcp__agent-knowledge__refresh_source",
    "mcp__agent-knowledge__forget_source",
]


def build_skill_text() -> str:
    if _BUNDLED_SKILL.exists():
        return _BUNDLED_SKILL.read_text(encoding="utf-8")
    # Fallback for installs where the repo skills/ directory is unavailable
    # (e.g. pip-installed without source). Keep in sync with skills/agent-knowledge-server/SKILL.md.
    return """---
name: agent-knowledge-server
description: Use when a user wants to save useful content to agent knowledge, search saved knowledge, or forget incorrect saved knowledge
---

# agent-knowledge-server

Use this skill when the user wants to interact with the agent knowledge MCP.

## Setup

- Install or refresh the skill and MCP registration with `agent-knowledge-server install`.
- After installation, start a new assistant session before relying on the MCP tools.
- The installer is expected to write the MCP config and Claude permissions for you.
- If Codex or Claude can see this skill but the MCP tools are missing or still prompting too much, inspect the local MCP config before doing knowledge work.

### Codex Setup

- Codex uses `~/.codex/config.toml`, not `settings.json`, for MCP registration and approval defaults.
- `agent-knowledge-server install` should ensure `~/.codex/config.toml` contains:

```toml
[mcp_servers.agent-knowledge]
command = "agent-knowledge-server"
args = ["serve"]
default_tools_approval_mode = "approve"
```

- If you prefer tighter control, keep `default_tools_approval_mode = "prompt"` and set per-tool approval overrides instead.

### Claude Setup

- `agent-knowledge-server install` should register the Claude MCP server and update `~/.claude/settings.json`.
- The `permissions.allow` array should include:

```json
[
  "mcp__agent-knowledge__add_source",
  "mcp__agent-knowledge__add_text_source",
  "mcp__agent-knowledge__add_text_source_from_context",
  "mcp__agent-knowledge__import_pdf_folder",
  "mcp__agent-knowledge__list_sources",
  "mcp__agent-knowledge__list_documents",
  "mcp__agent-knowledge__search_knowledge",
  "mcp__agent-knowledge__refresh_source",
  "mcp__agent-knowledge__forget_source"
]
```

## Save Knowledge

- If the user wants to save useful knowledge from accessible content, normalize the content first.
- Prefer `add_text_source` for LLM-derived content provided by the user.
- Prefer `add_text_source_from_context` when the content is derived from the current assistant conversation context.
- Prefer `add_source` for a single explicit file path or URL.
- Prefer `import_pdf_folder` for a curated folder of PDFs that should become individual sources.
- Include a human-readable `source_label` whenever possible.

## Search Knowledge

- Use `search_knowledge` to find previously saved information.
- Use `list_sources` or `list_documents` when the user wants to inspect what is stored.

## Refresh Knowledge

- Use `refresh_source` when a source is stale or the user wants to re-index it from its original location.
- Requires `source_id`; use `list_sources` first if the id is unknown.

## Remove Wrong Knowledge

- If the user says content is wrong, stale, or should be removed, use `forget_source`.
- Prefer a natural target or label when possible, not only source ids.
"""


def default_skill_dirs() -> dict[str, Path]:
    return {
        "codex": Path.home() / ".codex" / "skills",
        "claude": Path.home() / ".claude" / "skills",
    }


def default_codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def default_claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


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


def _render_codex_server_block() -> str:
    return (
        f"{CODEX_SERVER_HEADER}\n"
        'command = "agent-knowledge-server"\n'
        'args = ["serve"]\n'
        'default_tools_approval_mode = "approve"\n'
    )


def _replace_toml_section(text: str, header: str, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip() != header:
            continue
        end = index + 1
        while end < len(lines):
            stripped = lines[end].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            end += 1
        replacement_text = replacement if replacement.endswith("\n") else f"{replacement}\n"
        updated = "".join(lines[:index]) + replacement_text
        if end < len(lines):
            updated += "".join(lines[end:])
        return updated

    if not text:
        return replacement if replacement.endswith("\n") else f"{replacement}\n"

    suffix = "" if text.endswith("\n") else "\n"
    replacement_text = replacement if replacement.endswith("\n") else f"{replacement}\n"
    return f"{text}{suffix}\n{replacement_text}"


def configure_codex_mcp(config_path: Path) -> str:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updated = _replace_toml_section(existing, CODEX_SERVER_HEADER, _render_codex_server_block())
    config_path.write_text(updated, encoding="utf-8")
    return f"Codex MCP: configured {config_path}"


def configure_claude_permissions(settings_path: Path) -> str:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        payload = {}

    permissions = payload.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    for tool_name in CLAUDE_ALLOWED_TOOLS:
        if tool_name not in allow:
            allow.append(tool_name)

    settings_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return f"Claude permissions: updated {settings_path}"


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
    return (
        "Ensure ~/.codex/config.toml contains "
        "[mcp_servers.agent-knowledge] command = \"agent-knowledge-server\", "
        "args = [\"serve\"], and default_tools_approval_mode = \"approve\", "
        "then restart the session."
    )


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
            messages.append(configure_claude_permissions(default_claude_settings_path()))
            ok, message = register_claude_mcp()
            prefix = "Claude MCP" if ok else "Claude MCP notice"
            messages.append(f"{prefix}: {message}")
        if "codex" in targets:
            messages.append(configure_codex_mcp(default_codex_config_path()))

    messages.append("Start a new assistant session after installation.")
    return messages
