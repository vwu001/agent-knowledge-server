# gw-docs-mcp

Local semantic search over Guidewire PDF documentation for Claude. Fully offline after first model download (~90MB). Three MCP tools: `search_gw_docs`, `list_gw_docs`, `reindex_gw_docs`; four CLI commands: `index`, `reset`, `status`, `configure`.

## Install

```bash
# 1. Install from GitHub
pip install git+https://github.com/vwu001/gw-docs-mcp.git

# 2. Register with Claude Code
claude mcp add --scope user gw-docs -- gw-docs-mcp serve

# 3. Point at your PDF directory
gw-docs-mcp configure --pdf-dir ~/gwdocs

# 4. Index (one-time; first run downloads ~90MB model)
gw-docs-mcp index

# 5. Verify
gw-docs-mcp status
```

Start a **new Claude Code session** after step 2 — MCP tools load at session start.

## Tools Available in Claude

| Tool | Description |
|---|---|
| `search_gw_docs(query)` | Semantic search — returns top matching snippets with source + page |
| `list_gw_docs()` | Show what PDFs are indexed and how many chunks each has |
| `reindex_gw_docs()` | Re-index after adding new PDFs |

## Example Queries

```
search_gw_docs("RowIterator read-only list view")
search_gw_docs("Gosu for loop syntax")
search_gw_docs("entity retireable marker")
search_gw_docs("Query.make orderBy")
search_gw_docs("SearchPanel criteria serializable")
```

## Supported PDFs

Drop any Guidewire PDF into your configured directory and run `gw-docs-mcp index`. Works with:
- UserInterfaceConfig.pdf
- GosuRules.pdf / GosuRefGuide.pdf
- DataModelConfig.pdf
- ConfigPC.pdf
- WorkflowConfig.pdf
- ProductModelGuide.pdf

## Storage

All data is local:
- `~/.gw-docs-mcp/chroma/` — vector index (ChromaDB)
- `~/.gw-docs-mcp/models/` — embedding model cache
- `~/.config/gw-docs-mcp/config.toml` — configuration

## Re-indexing

**Adding new PDFs** — incremental, upserts only new/changed chunks:
```bash
gw-docs-mcp index
# or from within Claude: reindex_gw_docs()
```

**PDF removed or renamed** — must wipe and rebuild the index from scratch:
```bash
gw-docs-mcp reset
# with -y to skip the confirmation prompt
gw-docs-mcp reset -y
```

`reset` deletes `~/.gw-docs-mcp/chroma/` then immediately re-indexes all PDFs in the configured directory. Use it any time the set of PDFs changes (removals or renames) — `index` alone will leave stale chunks from deleted files.
