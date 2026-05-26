# agent-knowledge-server — Rebuild Spec
2026-05-25

## Purpose

`agent-knowledge-server` is a local-first, curated personal knowledge base for coding agents. It accepts explicitly user-added sources — one file path or one URL at a time — indexes them into a local semantic vector store, and exposes search, listing, refresh, and forgetting over that index via both a CLI and an MCP server.

A user can also save LLM-accessible text directly into the knowledge base via `add_text_source`, without needing a dedicated parser or connector.

### Hard constraints

- No folder indexing, no link crawling, no auto-refresh
- Local files are referenced by their original path and never copied into app storage
- URLs are fetched once and snapshotted into app-owned storage
- All storage is local (`~/.config/` and `~/.local/share/`); no cloud dependencies after install

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Package build | `hatchling` |
| MCP server | `mcp >= 1.0.0` (stdio transport) |
| Vector store | `chromadb >= 0.5.0` (persistent local) |
| Embedding model | `sentence-transformers >= 3.0.0`, model `all-MiniLM-L6-v2` |
| PDF loading | `pymupdf >= 1.24.0` (imported as `fitz`) |
| CLI | `typer >= 0.12.0` |
| Config format | TOML — read with stdlib `tomllib`, written with `tomli-w >= 1.0.0` |
| Test runner | `pytest >= 8.0.0` |

The single installable entry point is `agent-knowledge-server` (CLI binary). The MCP server is launched via `agent-knowledge-server serve` over stdio.

---

## Package Structure

```
src/agent_knowledge_server/
  __init__.py
  config.py      — dataclasses + TOML load/save; no I/O side-effects at import
  registry.py    — SourceRecord, DocumentSummary, SourceRegistry (JSON file)
  loaders.py     — NormalizedDocument, per-format loaders, URL fetch+snapshot
  indexer.py     — Indexer: orchestrates add/refresh/forget via loaders+registry+chromadb
  searcher.py    — Searcher: search, list_sources, list_documents, find_sources
  server.py      — MCP server wiring; thin handlers that call Indexer/Searcher
  cli.py         — Typer CLI; thin commands that delegate to server handlers
  installer.py   — global skill file writing + Claude MCP registration
```

Dependency direction is strictly one-way: `cli` and `server` → `indexer` and `searcher` → `registry` and `loaders` → `config`. Nothing in the lower layers imports from the upper layers.

---

## Data Model

### SourceRecord
Persisted in `registry.json`, one per user-added source.

```
source_id       str   — "{kind}-{sha1(original)[:12]}"
kind            str   — "file" | "url" | "text"
original        str   — resolved file path, URL, or original_ref/source_label
source_label    str   — human-readable label (required for text sources)
content_type    str   — "pdf" | "markdown" | "html" | "text"
title           str   — extracted or inferred title
status          str   — "pending" | "indexed" | "failed"
created_at      str   — ISO 8601 UTC
updated_at      str   — ISO 8601 UTC
last_indexed_at str   — ISO 8601 UTC
fingerprint     str   — sha1 of all document content joined
error           str   — last error message when status == "failed"
documents       list[DocumentSummary]
```

### DocumentSummary
Embedded inside SourceRecord. One per page or section produced by the loader.

```
document_id     str   — "{source_id}::p{N}" for PDF pages, "{source_id}::root" for others
title           str
content_type    str
location        str   — page number string for PDFs; empty otherwise
```

### NormalizedDocument
In-memory only. Produced by loaders, consumed by the indexer.

```
document_id     str
title           str
content         str
content_type    str
metadata        dict  — {"page": int} for PDF; {"url": str} for URL; {} otherwise
```

### Chunk metadata (stored in ChromaDB)
Stored alongside each embedded chunk vector.

```
source_id, document_id, source_title, source_kind, content_type,
original, title, page (int), section_path (str)
```

Chunk IDs follow the pattern: `"{source_id}::{document_id}::c{idx}"`

### SearchResult
Returned from `Searcher.search()`.

```
text        str
source_id   str
title       str
original    str
page        int
score       float   — 1.0 - cosine_distance, rounded to 4 decimal places
```

---

## Storage Layout

```
~/.config/agent-knowledge-server/
  config.toml                          — optional; defaults used if absent

~/.local/share/agent-knowledge-server/
  sources/
    registry.json                      — JSON object keyed by source_id
    <source-id>/
      snapshot.html                    — URL sources only: raw fetched HTML
      content.txt                      — text sources only: provided content
      notes.txt                        — text sources only, optional
  chroma/                              — ChromaDB persistent storage
  models/                              — sentence-transformers model cache
```

Rules:
- File sources write nothing to `sources/<source-id>/` — they reference the original path only
- `forget_source` removes the `sources/<source-id>/` directory (if it exists), deletes ChromaDB chunks keyed by `source_id`, then deletes the registry entry — in that order, idempotently
- `registry.json` is the authoritative source list; ChromaDB is the derived search index

### config.toml schema (all keys optional)

```toml
[search]
top_k = 5
chunk_size = 500
chunk_overlap = 50

[model]
name = "all-MiniLM-L6-v2"
cache_dir = ""   # defaults to ~/.local/share/agent-knowledge-server/models

[paths]
# all path overrides are optional; defaults shown in storage layout above
```

---

## CLI Surface

All commands delegate to the same handler functions used by the MCP server.

```
agent-knowledge-server add --file <path>
agent-knowledge-server add --url <url>

agent-knowledge-server add-text \
  --source-label <label> \
  --content <text> \
  [--title <str>] \
  [--source-kind <str>] \
  [--original-ref <str>] \
  [--notes <str>]

agent-knowledge-server import-pdfs --dir <path> [--pattern <glob>]
  # default pattern: *.pdf

agent-knowledge-server list-sources
agent-knowledge-server list-documents
agent-knowledge-server search <query> [--top-k N]
agent-knowledge-server refresh --source-id <id>

agent-knowledge-server forget --source-id <id> [-y/--yes]
agent-knowledge-server forget --target <label>  [-y/--yes]

agent-knowledge-server status
agent-knowledge-server serve

agent-knowledge-server install
  [--mcp-only]
  [--skill-only]
  [--codex]
  [--claude]
```

**Error rules:**
- `add` with both `--file` and `--url`, or neither: print error to stderr, exit 1
- `--mcp-only` and `--skill-only` together: print error to stderr, exit 1
- `forget` without `--source-id` or `--target`: print error to stderr, exit 1
- `forget` without `--yes`: prompt for confirmation; abort if declined

**Output format for `list-sources`:**
```
Source ID          Kind   Status   Label
------------------------------------------------------------------------
file-abc123...     file   indexed  My Guide
url-def456...      url    indexed  https://example.com/page
```

---

## MCP Tool Surface

Server name: `agent-knowledge`. Transport: stdio.

| Tool | Required | Optional |
|---|---|---|
| `add_source` | one of `file_path` or `url` | — |
| `add_text_source` | `content`, `source_label` | `title`, `source_kind`, `original_ref`, `notes` |
| `add_text_source_from_context` | `content`, `source_label` | same as above |
| `import_pdf_folder` | `dir` | `pattern` (default `*.pdf`) |
| `list_sources` | — | — |
| `list_documents` | — | — |
| `search_knowledge` | `query` | `top_k` |
| `refresh_source` | `source_id` | — |
| `forget_source` | at least one of `source_id`, `source_label`, `original_ref`, `fuzzy_target` | — |

All tools return `list[TextContent]` with a single plain text string.

`add_text_source` and `add_text_source_from_context` use the same handler and schema.

**`forget_source` resolution order:**
1. Exact `source_id` match
2. Exact `source_label` match
3. Exact `original` match
4. Fuzzy substring match on label, title, and original

→ 0 matches: return failure message  
→ 1 match: forget it, return `"Forgot source_id={id}"`  
→ 2+ matches: return disambiguation message listing `{source_id} ({label})` for each candidate

---

## Ingestion Pipeline

The same pipeline handles all three source kinds.

1. **Upsert registry record** — create or update a `SourceRecord` (status: `pending`)
2. **Load** — call the appropriate loader, receive `list[NormalizedDocument]` and a `meta` dict
3. **Delete existing chunks** — `collection.delete(where={"source_id": source_id})` before inserting (safe no-op if none exist)
4. **Chunk** — word-based sliding window: split on whitespace, default 500 words per chunk, 50-word overlap; if content is ≤500 words, produce one chunk
5. **Embed** — `SentenceTransformer.encode(chunks, show_progress_bar=False)` in batch
6. **Upsert into ChromaDB** — chunk IDs as `"{source_id}::{document_id}::c{idx}"` with embeddings, text, and chunk metadata
7. **Update registry** — set `status="indexed"`, `last_indexed_at`, `fingerprint`, and `documents` list; persist to `registry.json`

On any exception in steps 2–7: set `status="failed"`, store error string in `record.error`, persist, re-raise.

### Loaders

| Input | Behavior | document_id pattern |
|---|---|---|
| `.pdf` | `fitz.open()` — one doc per non-empty page | `"{filename}::p{N}"`, `metadata={"page": N+1}` |
| `.md` / `.markdown` | Strip `#*_>-` chars, collapse whitespace, extract first `#` heading as title | `"{filename}::root"` |
| `.txt` | Read raw; file stem as title | `"{filename}::root"` |
| `.html` / `.htm` | `html.parser.HTMLParser` — extract `<title>` and visible text | `"{filename}::root"` |
| URL | `urllib.request.urlopen` with `User-Agent: agent-knowledge-server`, 20s timeout; save raw to `snapshot.html`; parse as HTML | `"url::{sha1(url)}"` |
| text source | Content passed directly; write to `content.txt` | `"{source_id}::root"` |

Unsupported file extensions raise `ValueError` immediately.

---

## Installer

`agent-knowledge-server install` performs two actions: write a global skill file and register the MCP server.

### Skill file

Written to:
- `~/.claude/skills/agent-knowledge-server/SKILL.md` (Claude target)
- `~/.codex/skills/agent-knowledge-server/SKILL.md` (Codex target)

Directories are created if missing. The skill content teaches the assistant:
- Use `add_text_source` for LLM-derived content; `add_source` for a single file or URL; `import_pdf_folder` for a curated PDF folder
- Always include a human-readable `source_label`
- Use `search_knowledge` to retrieve; `list_sources`/`list_documents` to inspect
- Use `forget_source` with a natural label when the user says something is wrong or stale

### MCP registration

Claude (automated): `claude mcp add --scope user agent-knowledge -- agent-knowledge-server serve`
- Requires the `claude` CLI on PATH
- If not found: print manual registration instructions instead

Codex: skill file is written; MCP registration prints guidance only (no automation).

### Target selection

- Default: both `codex` and `claude`
- `--codex` or `--claude` restricts to one target
- `--mcp-only` skips skill writing; `--skill-only` skips MCP registration
- `--mcp-only` + `--skill-only` together: exit 1

### Verification output

The install command prints, in order:
1. Full path to each skill file written
2. MCP registration result or manual step required
3. Always ends with: `"Start a new assistant session after installation."`

---

## Testing Strategy

### File layout

```
tests/
  conftest.py
  test_config.py
  test_registry.py
  test_loaders.py
  test_indexer.py
  test_searcher.py
  test_server.py
  test_cli.py
  test_installer.py
  test_integration.py
```

### Unit tests — fast, mocked embeddings

Mock `SentenceTransformer.encode` to return deterministic zero vectors. Use `tmp_path` fixtures for all file I/O. Mock `urllib.request.urlopen` in all non-integration tests.

**test_config**
- Load defaults when no config file exists
- Override each field from a TOML file
- `save_config` + `load_config` round-trip preserves all values

**test_registry**
- `upsert_file`, `upsert_url`, `upsert_text` create a `SourceRecord` with correct `source_id` format
- Duplicate upsert updates the record, does not create a second entry
- `delete` removes only the target record, leaves others
- `list_sources` returns records sorted by `updated_at` descending

**test_loaders**
- Each file type (PDF, Markdown, text, HTML) returns correctly shaped `NormalizedDocument`
- PDF loader produces one doc per non-empty page with `metadata={"page": N}`
- Unsupported extension raises `ValueError`
- URL loader: mock `urlopen` with fake HTML; assert snapshot file is written; assert correct title is extracted

**test_indexer**
- `add_file_source` calls loader, calls ChromaDB upsert, updates registry with `status="indexed"`
- `forget_source` deletes ChromaDB chunks, removes source directory, deletes registry entry
- `refresh_source` re-runs the add path for both file and URL kinds
- Failed indexing sets `status="failed"` and stores error string; does not leave stale chunks

**test_searcher**
- `find_sources` respects resolution order: exact id → exact label → exact original → fuzzy
- `find_sources` returns empty list for no-match input
- `list_documents` flattens `DocumentSummary` records across all sources

**test_server**
- Each MCP handler returns a non-empty string
- `handle_forget` with ambiguous target returns disambiguation message
- `handle_forget` with no match returns failure message
- `handle_add` with both `file_path` and `url` returns error string

**test_cli**
- `add` with both `--file` and `--url` exits 1
- `forget` without `--source-id` or `--target` exits 1
- `install --mcp-only --skill-only` exits 1
- Valid `search` command invokes `handle_search` and prints result
- `forget` without `--yes` triggers confirmation prompt

**test_installer**
- `build_skill_text()` contains keywords: `add_text_source`, `add_source`, `search_knowledge`, `forget_source`
- `install_global_skill` writes the skill file at the expected path and creates missing directories
- `register_claude_mcp` with `claude` not on PATH returns `(False, <instructions string>)`
- `install_everything` returns a list ending with the new-session reminder

### Integration tests — real embedding model, tmp dirs

- Add a PDF file source, search for content known to be in the PDF, assert results are non-empty and carry the correct `source_id`
- Add a text source, search for content from it, forget it by `source_id`, search again, assert no results
- Add two sources, forget one by fuzzy label match, assert only the correct source is removed and the other is still searchable
- Refresh a URL source (mock the second fetch with updated content), assert `last_indexed_at` is updated and old chunk content is replaced

Integration tests may be slow — mark with `pytest.mark.integration` and skip by default in CI if needed.
