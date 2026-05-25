# local-knowledge-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `gw-docs-mcp` with `local-knowledge-mcp`, then add explicit file and URL source management with generic loaders, source-aware indexing, and wiki-style listing workflows.

**Architecture:** Perform a hard package and surface rename first so the code and docs match the new product. Then add a source registry plus loader pipeline that normalizes one source at a time into documents and chunks, with URL snapshots stored under app-owned data and local files re-read from their original paths.

**Tech Stack:** Python 3.11+, Typer, MCP SDK, PyMuPDF, sentence-transformers, ChromaDB, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `AGENTS.md` | Repo instructions for Codex and other coding agents |
| `pyproject.toml` | Package name, dependencies, entry point |
| `README.md` | User-facing install and usage docs |
| `claude-plugin.json` | MCP server registration metadata |
| `src/local_knowledge_mcp/config.py` | New config and application path model |
| `src/local_knowledge_mcp/registry.py` | Persistent source registry |
| `src/local_knowledge_mcp/loaders.py` | File and URL loaders to normalized documents |
| `src/local_knowledge_mcp/indexer.py` | Source-aware indexing pipeline |
| `src/local_knowledge_mcp/searcher.py` | Search, source listing, document listing |
| `src/local_knowledge_mcp/server.py` | Generic MCP tools |
| `src/local_knowledge_mcp/cli.py` | Add/list/search/refresh/forget CLI |
| `tests/` | Coverage for rename, config, registry, loaders, search, server, CLI |

## Task 1: Hard Rename Skeleton

**Files:**
- Modify: `pyproject.toml`
- Modify: `claude-plugin.json`
- Modify: `README.md`
- Create: `src/local_knowledge_mcp/__init__.py`
- Remove or replace imports under `src/gw_docs_mcp/`

- [ ] Rename the package and binary to `local-knowledge-mcp`.
- [ ] Replace GW-specific copy in metadata and docs.
- [ ] Update imports and test references to the new module path.

## Task 2: Config and App Paths

**Files:**
- Modify: `src/local_knowledge_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] Red: add tests for new default config path and app data layout.
- [ ] Green: implement app-owned config, data, models, source, and chroma paths.
- [ ] Refactor: keep config dataclasses small and path helpers explicit.

## Task 3: Source Registry

**Files:**
- Create: `src/local_knowledge_mcp/registry.py`
- Create: `tests/test_registry.py`

- [ ] Red: add tests for add, update, list, and forget of explicit file and URL sources.
- [ ] Green: implement `SourceRecord` and persistent registry storage.
- [ ] Refactor: centralize source-id creation and metadata updates.

## Task 4: Generic Loaders

**Files:**
- Create: `src/local_knowledge_mcp/loaders.py`
- Test: `tests/test_loaders.py`

- [ ] Red: add tests for PDF, markdown, text, HTML, and URL snapshot loading.
- [ ] Green: implement normalized document extraction for supported types.
- [ ] Refactor: keep each loader isolated behind one dispatch function.

## Task 5: Source-Aware Indexing and Search

**Files:**
- Modify: `src/local_knowledge_mcp/indexer.py`
- Modify: `src/local_knowledge_mcp/searcher.py`
- Test: `tests/test_indexer.py`
- Test: `tests/test_searcher.py`

- [ ] Red: add tests for per-source indexing, refresh replacement, and targeted forgetting.
- [ ] Green: implement source-aware chunk metadata and per-source deletion.
- [ ] Refactor: keep chunking generic and move source lifecycle logic out of search formatting.

## Task 6: CLI and MCP Surface

**Files:**
- Modify: `src/local_knowledge_mcp/cli.py`
- Modify: `src/local_knowledge_mcp/server.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_server.py`

- [ ] Red: add tests for `add`, `list-sources`, `list-documents`, `search`, `refresh`, and `forget`.
- [ ] Green: implement the new CLI commands and MCP tools.
- [ ] Refactor: share formatting helpers where practical without overengineering.

## Task 7: Final Docs and Verification

**Files:**
- Modify: `README.md`
- Review: `docs/superpowers/specs/2026-05-25-local-knowledge-mcp-design.md`

- [ ] Update docs to match the shipped contract.
- [ ] Run the full pytest suite.
- [ ] Review the final diff against the approved spec and note any intentional deferrals.
