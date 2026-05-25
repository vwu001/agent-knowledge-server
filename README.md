# local-knowledge-mcp

Local MCP knowledge server for explicitly curated sources. Add one file path or one URL at a time, index it locally, then search, list, refresh, or forget that source.

## Install

```bash
pip install git+https://github.com/vwu001/local-knowledge-mcp.git
local-knowledge-mcp install
```

`local-knowledge-mcp install` installs the global assistant skill and attempts MCP registration for supported targets. Start a new assistant session after installation so the MCP tools and skill are available.

## Core Actions

```bash
local-knowledge-mcp add --file ~/docs/guide.pdf
local-knowledge-mcp add --url https://example.com/page
local-knowledge-mcp add-text --source-label "Confluence Pricing Guide" --content "Normalized page content"
local-knowledge-mcp list-sources
local-knowledge-mcp list-documents
local-knowledge-mcp search "database queries"
local-knowledge-mcp refresh --source-id file-123abc
local-knowledge-mcp forget --source-id url-456def
local-knowledge-mcp forget --target "pricing guide"
```

## MCP Tools

- `add_source`
- `add_text_source`
- `add_text_source_from_context`
- `list_sources`
- `list_documents`
- `search_knowledge`
- `refresh_source`
- `forget_source`

## Supported Inputs

- PDF
- Markdown
- plain text
- HTML
- one URL at a time, with a stored snapshot

Folder indexing and crawling are intentionally out of scope.

## LLM-Assisted Ingestion

If Codex or Claude can already read the content, they can save it directly into local knowledge without a dedicated parser or connector. The intended pattern is:

- extract or normalize the useful content
- call `add_text_source` with `content` and `source_label`
- later remove it with `forget_source` using a natural target if the saved knowledge is wrong

This is useful for browser-visible pages, pasted content, repo notes, Confluence pages, and other assistant-accessible material.

## Installer Modes

```bash
local-knowledge-mcp install
local-knowledge-mcp install --mcp-only
local-knowledge-mcp install --skill-only
local-knowledge-mcp install --codex
local-knowledge-mcp install --claude
```

## Storage

- `~/.config/local-knowledge-mcp/config.toml`
- `~/.local/share/local-knowledge-mcp/sources/`
- `~/.local/share/local-knowledge-mcp/chroma/`
- `~/.local/share/local-knowledge-mcp/models/`
