# agent-knowledge-server

Curated agent knowledge server for coding agents. Add one file path or one URL at a time, or let the assistant save normalized text directly, then search, list, refresh, or forget that knowledge.

## Install

```bash
pip install git+https://github.com/vwu001/agent-knowledge-server.git
agent-knowledge-server install
```

`agent-knowledge-server install` installs the global assistant skill and attempts MCP registration for supported targets. Start a new assistant session after installation so the MCP tools and skill are available.

## Core Actions

```bash
agent-knowledge-server add --file ~/docs/guide.pdf
agent-knowledge-server add --url https://example.com/page
agent-knowledge-server add-text --source-label "Confluence Pricing Guide" --content "Normalized page content"
agent-knowledge-server import-pdfs --dir ~/docs/curated-pdfs
agent-knowledge-server list-sources
agent-knowledge-server list-documents
agent-knowledge-server search "database queries"
agent-knowledge-server refresh --source-id file-123abc
agent-knowledge-server forget --source-id url-456def
agent-knowledge-server forget --target "pricing guide"
```

## MCP Tools

- `add_source`
- `add_text_source`
- `add_text_source_from_context`
- `import_pdf_folder`
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
- curated PDF folders imported as individual PDF sources

Folder indexing and crawling are intentionally out of scope.

## Curated PDF Batch Import

If you have a trusted folder of PDFs you want in the knowledge base, use:

```bash
agent-knowledge-server import-pdfs --dir ~/docs/curated-pdfs
```

This imports each PDF as its own file source. After import, you can still list, refresh, and forget individual PDFs independently.

## LLM-Assisted Ingestion

If Codex or Claude can already read the content, they can save it directly into agent knowledge without a dedicated parser or connector. The intended pattern is:

- extract or normalize the useful content
- call `add_text_source` with `content` and `source_label`
- later remove it with `forget_source` using a natural target if the saved knowledge is wrong

This is useful for browser-visible pages, pasted content, repo notes, Confluence pages, and other assistant-accessible material.

## Installer Modes

```bash
agent-knowledge-server install
agent-knowledge-server install --mcp-only
agent-knowledge-server install --skill-only
agent-knowledge-server install --codex
agent-knowledge-server install --claude
```

## Storage

- `~/.config/agent-knowledge-server/config.toml`
- `~/.local/share/agent-knowledge-server/sources/`
- `~/.local/share/agent-knowledge-server/chroma/`
- `~/.local/share/agent-knowledge-server/models/`

## Runtime Notes

- Search uses the existing Chroma collection without trying to create or mutate it, so queries against an already indexed read-only Chroma store continue to work.
- Mutating operations (`add`, `add-text`, `import-pdfs`, `refresh`, `forget`) are serialized with a local file lock at `~/.local/share/agent-knowledge-server/.write.lock` to avoid concurrent write races when multiple agents share one data directory.
