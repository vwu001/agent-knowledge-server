# gw-docs-mcp

Local semantic search over Guidewire PDF documentation for Claude. Fully offline after first model download (~90MB). Three MCP tools: `search_gw_docs`, `list_gw_docs`, `reindex_gw_docs`.

## Install

```bash
# 1. Clone and install
git clone https://github.com/vwu001/gw-docs-mcp
cd gw-docs-mcp
pip install -e .

# 2. Register with Claude Code (add to ~/.claude/settings.json)
{
  "mcpServers": {
    "gw-docs": {
      "command": "gw-docs-mcp",
      "args": ["serve"]
    }
  }
}

# 3. Point at your PDF directory
gw-docs-mcp configure --pdf-dir ~/path/to/gw-pdfs

# 4. Index (one-time, ~1-2 min per 100 pages, first run downloads ~90MB model)
gw-docs-mcp index

# 5. Verify
gw-docs-mcp status
```

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

When you add new PDFs:
```bash
gw-docs-mcp index
# or from within Claude: reindex_gw_docs()
```
