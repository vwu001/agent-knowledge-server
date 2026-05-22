# gw-docs-mcp — Design Spec
Draft 1.0 | 2026-05-22

## Summary

A standalone Claude Code plugin that installs a local MCP server for semantic search over Guidewire PDF documentation. Fully offline after initial model download. Each developer points it at their local PDF directory; the server indexes the docs once and answers search queries returning only the relevant snippet — no whole-page context dumps, no internet dependency.

---

## 1. Goals

- Give Claude on-demand access to GW reference docs without loading entire PDFs into context
- Run completely offline (no Confluence, no cloud APIs)
- Install once per developer machine via `claude install`
- Work across any GW project (PolicyCenter, BillingCenter, ClaimCenter, etc.)
- Return source attribution (PDF filename + page number) with every result

---

## 2. Repo

**GitHub:** `https://github.com/vwu001/gw-docs-mcp`
**Local dev path:** `/Users/vincentwu/dev/aibuild/tools/gw-docs-mcp`

---

## 3. Architecture

### 3.1 Components

**Indexer (`indexer.py`)**
- Runs once at setup, and on demand when PDFs change
- Extracts text from PDFs using `PyMuPDF` (fitz)
- Chunks text into ~500-token paragraphs, preserving source filename and page number
- Embeds chunks using `sentence-transformers/all-MiniLM-L6-v2` (90MB, downloaded once, then offline)
- Stores embeddings in a local `ChromaDB` collection at `~/.gw-docs-mcp/chroma/`

**MCP Server (`server.py`)**
- Python process using the `mcp` SDK
- Registered in Claude's MCP config at install time
- Exposes three tools (see Section 5)
- Reads config from `~/.config/gw-docs-mcp/config.toml`

**CLI (`cli.py`)**
- `gw-docs-mcp configure --pdf-dir <path>` — writes config file
- `gw-docs-mcp index` — runs the indexer
- `gw-docs-mcp status` — shows what is indexed and how many chunks

**Plugin Manifest (`claude-plugin.json`)**
- Declares the MCP server entry point
- Wires into Claude Code's plugin system on `claude install`

### 3.2 Data Flow

```
PDF files (local, user-specified directory)
  ↓ PyMuPDF — extract text per page
  ↓ Chunk into ~500 token paragraphs (overlap 50 tokens)
  ↓ Embed with all-MiniLM-L6-v2 (local, offline after first download)
  ↓ Store in ChromaDB (~/.gw-docs-mcp/chroma/)

Claude query
  → MCP server receives search_gw_docs(query)
  → Embed query with same model
  → ChromaDB cosine similarity search → top-k chunks
  → Return [{text, source_pdf, page, score}]
```

### 3.3 Storage Layout

```
~/.gw-docs-mcp/
  chroma/              ← ChromaDB vector store (local SQLite)
  models/              ← cached sentence-transformers model

~/.config/gw-docs-mcp/
  config.toml          ← pdf_dir, top_k defaults
```

---

## 4. File Structure

```
gw-docs-mcp/
  src/
    gw_docs_mcp/
      __init__.py
      server.py        ← MCP server, tool definitions
      indexer.py       ← PDF extraction + embedding pipeline
      searcher.py      ← ChromaDB query wrapper
      config.py        ← config file read/write
      cli.py           ← configure / index / status commands
  docs/
    2026-05-22-gw-docs-mcp-design.md
  claude-plugin.json   ← Claude Code plugin manifest
  pyproject.toml       ← package definition, dependencies
  .gitignore
  README.md
```

---

## 5. MCP Tools

### `search_gw_docs`

Search indexed GW documentation for the most relevant content.

**Parameters:**
- `query` (string, required) — natural language or keyword query
- `top_k` (integer, optional, default 5) — number of results to return

**Returns:** Array of result objects:
```json
[
  {
    "text": "RowIterator requires editable='false' on all read-only list views...",
    "source": "UserInterfaceConfig.pdf",
    "page": 34,
    "score": 0.91
  }
]
```

### `list_gw_docs`

List all indexed PDFs with chunk counts.

**Returns:**
```json
[
  {"filename": "UserInterfaceConfig.pdf", "pages": 96, "chunks": 412},
  {"filename": "GosuRules.pdf", "pages": 22, "chunks": 98}
]
```

### `reindex_gw_docs`

Re-run the indexer. Useful when new PDFs are added to the configured directory.

**Parameters:**
- `pdf_dir` (string, optional) — override the configured directory for this run

**Returns:** Summary of indexed files and chunk counts.

---

## 6. Configuration File

Location: `~/.config/gw-docs-mcp/config.toml`

```toml
[docs]
pdf_dir = "/Users/vincentwu/Downloads"

[search]
top_k = 5
chunk_size = 500
chunk_overlap = 50

[model]
name = "all-MiniLM-L6-v2"
cache_dir = "~/.gw-docs-mcp/models"

[chroma]
persist_dir = "~/.gw-docs-mcp/chroma"
collection = "gw_docs"
```

---

## 7. Claude Code Plugin Manifest

`claude-plugin.json`:
```json
{
  "name": "gw-docs-mcp",
  "version": "1.0.0",
  "description": "Local semantic search over Guidewire PDF documentation",
  "mcp_servers": {
    "gw-docs": {
      "command": "python",
      "args": ["-m", "gw_docs_mcp.server"],
      "description": "Search Guidewire docs locally"
    }
  }
}
```

---

## 8. Install Flow

```bash
# 1. Install the plugin
claude install github:vwu001/gw-docs-mcp

# 2. Point it at your PDF directory
gw-docs-mcp configure --pdf-dir ~/Downloads

# 3. Index the docs (one-time, ~1-2 min per 100 pages)
gw-docs-mcp index

# 4. Verify
gw-docs-mcp status
```

After step 4, Claude has `search_gw_docs`, `list_gw_docs`, and `reindex_gw_docs` available in every session.

---

## 9. Dependencies

| Package | Purpose |
|---|---|
| `mcp` | MCP server SDK |
| `pymupdf` | PDF text extraction |
| `sentence-transformers` | Local embedding model |
| `chromadb` | Local vector store |
| `typer` | CLI framework |
| `tomllib` / `tomli` | Config file parsing |

All run locally. `sentence-transformers` downloads the model on first use (~90MB), then operates offline.

---

## 10. Non-Goals

- No cloud APIs or internet dependency after initial model download
- No GUI
- No multi-user server — this is a per-developer local tool
- No support for non-PDF formats in v1 (Word, HTML, etc.)
- No GW-specific filtering in v1 — all PDFs in the directory are indexed together

---

## 11. How AGENTS-*.md Files Use This

Each topic file in the policycenter repo will include a note at the top:

```
For deep reference beyond these rules, use:
  search_gw_docs("your topic here")
```

Example queries:
- `search_gw_docs("RowIterator attributes PCF")` → UserInterfaceConfig.pdf relevant section
- `search_gw_docs("Gosu for loop syntax")` → GosuRules.pdf relevant section
- `search_gw_docs("entity retireable marker columns")` → DataModelConfig.pdf relevant section
