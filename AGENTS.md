# AGENTS.md

## Project Purpose

This repository is evolving from `gw-docs-mcp` into `agent-knowledge-server`, an agent knowledge server for explicitly curated sources.

A source is exactly one:

- local file path, or
- URL

The server indexes only explicitly added sources and exposes add, list, search, refresh, forget, and list-documents workflows.

## Working Rules

- Preserve the approved design in `docs/superpowers/specs/2026-05-25-agent-knowledge-server-design.md`.
- Treat this as a hard rename. Do not keep GW-branded aliases unless the user explicitly asks for them.
- Do not add folder indexing or URL crawling.
- Local files are referenced by original path and are not copied into app storage.
- URLs are snapshotted into app-owned storage and can be forgotten independently.
- Keep the system local-first and deterministic.

## Implementation Priorities

1. Rename the package, CLI, config paths, storage paths, and MCP tool names.
2. Introduce a persistent source registry keyed by `source_id`.
3. Add generic loaders for PDF, Markdown, text, and HTML.
4. Add URL fetch-and-snapshot support.
5. Ensure indexed chunks are keyed by `source_id` so one source can be refreshed or forgotten safely.
6. Keep tests focused on behavior and run them before making completion claims.

## Codex Knowledge Workflow

- When the user asks to save useful knowledge from content already visible or accessible in Codex, normalize the useful text first and prefer `add_text_source` style ingestion over inventing a new parser.
- Include both `content` and a human-readable `source_label` when adding LLM-derived knowledge.
- When the user says something is wrong and should be removed from knowledge, prefer `forget_source` with the best available label or target context before asking for an exact id.

## Verification

- Prefer TDD: write a failing test first, then implement the smallest passing change.
- Run targeted tests during development and the full test suite before claiming completion.
