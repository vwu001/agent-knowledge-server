from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from agent_knowledge_server.tools import TOOL_NAMES

SKILL_NAME = "agent-knowledge-server"
SERVER_NAME = "agent-knowledge"
CODEX_SERVER_HEADER = f"[mcp_servers.{SERVER_NAME}]"
REPO_URL = "https://github.com/vwu001/agent-knowledge-server.git"

# Derived from the server's own tool list so a new tool is pre-approved rather
# than prompting on every call.
CLAUDE_ALLOWED_TOOLS = [f"mcp__{SERVER_NAME}__{name}" for name in TOOL_NAMES]

# Where SKILL.md lives, in preference order: bundled inside the installed wheel,
# then the repo checkout (editable installs and test runs). There is deliberately
# no inline copy -- a second copy of the skill text drifts from the real one.
_SKILL_CANDIDATES = (
    Path(__file__).parent / "_skills" / SKILL_NAME / "SKILL.md",
    Path(__file__).resolve().parents[2] / "skills" / SKILL_NAME / "SKILL.md",
)


def bundled_skill_path() -> Path:
    for candidate in _SKILL_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in _SKILL_CANDIDATES)
    raise FileNotFoundError(f"Could not locate the bundled SKILL.md. Searched: {searched}")


def build_skill_text() -> str:
    return bundled_skill_path().read_text(encoding="utf-8")


def is_uv_tool_install() -> bool:
    """True when this package was installed via `uv tool install`.

    uv tool environments live under the uv tools dir and have no usable pip, so
    `pip install --upgrade` fails there.
    """
    marker = f"{os.sep}uv{os.sep}tools{os.sep}"
    return marker in str(Path(sys.prefix).resolve()) or (Path(sys.prefix) / "uv-receipt.toml").exists()


def upgrade_command() -> list[str]:
    if is_uv_tool_install():
        return ["uv", "tool", "upgrade", "agent-knowledge-server"]
    # Not published to PyPI -- upgrade from the git remote the README installs from.
    return [sys.executable, "-m", "pip", "install", "--upgrade", "-q", f"git+{REPO_URL}"]


def run_upgrade() -> tuple[bool, str]:
    command = upgrade_command()
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        return False, (proc.stderr or "").strip() or f"Upgrade failed: {' '.join(command)}"
    return True, (proc.stdout or "").strip() or f"Upgraded via: {' '.join(command)}"


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


COMMAND_NAME = "agent-knowledge-server"


def server_command() -> str:
    """The command agents should launch to start the MCP server.

    Prefers the bare name, which stays correct if the install later moves. But a
    virtualenv install puts the console script in <venv>/bin, which is not on
    PATH unless the venv is activated -- and agents launch the server with the
    user's PATH, not an activated shell. In that case the bare name resolves to
    nothing (or to a different install) and the MCP server silently fails to
    connect, so write this install's absolute path instead.
    """
    local = Path(sys.executable).parent / COMMAND_NAME
    on_path = shutil.which(COMMAND_NAME)
    if local.exists():
        if on_path and Path(on_path).resolve() == local.resolve():
            return COMMAND_NAME
        return str(local)
    return on_path or COMMAND_NAME


def command_path_warning() -> str | None:
    """Explain the absolute-path fallback, or None when the bare name works."""
    command = server_command()
    if command == COMMAND_NAME:
        return None
    return (
        f"Notice: {COMMAND_NAME} is not on your PATH, so the MCP config points at "
        f"{command} instead. That works, but it breaks if the environment moves or is "
        f"deleted. For a durable install use: uv tool install ."
    )


def _render_codex_server_block() -> str:
    return (
        f"{CODEX_SERVER_HEADER}\n"
        f'command = "{server_command()}"\n'
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
        return False, (
            "Claude CLI not found. Install it, then run: "
            f"claude mcp add --scope user {SERVER_NAME} -- {server_command()} serve"
        )
    try:
        proc = subprocess.run(
            ["claude", "mcp", "add", "--scope", "user", SERVER_NAME, "--", server_command(), "serve"],
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

        warning = command_path_warning()
        if warning:
            messages.append(warning)

    messages.append("Start a new assistant session after installation.")
    return messages
