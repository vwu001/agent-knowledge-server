# local-knowledge-mcp Installer Skill Design
Draft 1.0 | 2026-05-25

## Summary

Add a global installer flow for `local-knowledge-mcp` that can install both:

- the MCP server registration
- a global assistant skill for Codex and Claude

The default install path should set up both together, while also supporting split installation modes.

## Approved Decisions

- The installer should install globally for all future sessions
- The install flow should support both a unified install and split `mcp-only` or `skill-only` modes
- The global skill should teach the assistant when to use `add_source`, `add_text_source`, `search_knowledge`, and `forget_source`
- The installer should target both Codex and Claude when possible

## Command Shape

Recommended CLI:

- `local-knowledge-mcp install`
- `local-knowledge-mcp install --mcp-only`
- `local-knowledge-mcp install --skill-only`
- `local-knowledge-mcp install --codex`
- `local-knowledge-mcp install --claude`

Default behavior:

- install both skill and MCP registration
- attempt both Codex and Claude targets when available
- print clear partial-success output if one target is unavailable

## Global Skill

The installer should write a global skill artifact that teaches:

- save useful knowledge with `add_text_source` or `add_source`
- search knowledge with `search_knowledge`
- remove wrong knowledge with `forget_source`
- prefer human-readable labels and natural forget targets

## Target Directories

- Codex global skills directory when available
- Claude global skills directory when available

The installer should create missing assistant skill directories when safe to do so.

## MCP Registration

- Claude registration should be automatic when the `claude` CLI is available
- Codex install should at minimum install the global skill and print exact MCP registration guidance if stable automation is not available

## Verification

The install command should report:

- which skill files were written
- which MCP registrations succeeded
- what manual action remains, if any
- whether a new session is required
