---
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
