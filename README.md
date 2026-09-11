# agent-knowledge-server

Curated agent knowledge server for coding agents. Add one file path or one URL at a time, or let the assistant save normalized text directly, then search, list, refresh, or forget that knowledge.

## Install

```bash
pip install git+https://github.com/vwu001/agent-knowledge-server.git
agent-knowledge-server install
```

`agent-knowledge-server install` installs the global assistant skill, writes the Codex MCP config, updates Claude MCP tool permissions, and attempts Claude MCP registration. Start a new assistant session after installation so the MCP tools and skill are available.

Codex uses `~/.codex/config.toml` for MCP setup, not `settings.json`. The installer writes:

```toml
[mcp_servers.agent-knowledge]
command = "agent-knowledge-server"
args = ["serve"]
default_tools_approval_mode = "approve"
```

Claude uses `~/.claude/settings.json` for tool permissions. The installer updates `permissions.allow` with the `mcp__agent-knowledge__...` tools written in the generated skill.

## Core Actions

```bash
agent-knowledge-server add --file ~/docs/guide.pdf
agent-knowledge-server add --file ~/docs/guide.pdf --source-label "BillingCenter Config 2026.07"
agent-knowledge-server add --url https://example.com/page --source-label "APD adoption guide"
agent-knowledge-server add-text --source-label "Confluence Pricing Guide" --content "Normalized page content"
agent-knowledge-server import-pdfs --dir ~/docs/curated-pdfs
agent-knowledge-server sync ~/docs/curated-pdfs
agent-knowledge-server list-sources
agent-knowledge-server list-documents
agent-knowledge-server search "database queries"
agent-knowledge-server refresh --source-id file-123abc
agent-knowledge-server forget --source-id url-456def
agent-knowledge-server forget --target "pricing guide"
```

## MCP Tools

- `add_source` (optional `source_label`, `force`)
- `add_text_source`
- `add_text_source_from_context`
- `import_pdf_folder`
- `sync_folder`
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

## Empty-Extraction Guard

A source is only recorded as `indexed` if something usable came out of it. If the
extracted text is empty, or is a JavaScript app shell rather than page content, the
add is refused, the source is recorded with `status="empty"` and an explanatory
`error`, and `list_sources` shows both.

This exists because the URL fetcher uses `urllib` and **does not execute JavaScript**.
Pointed at a single-page-app documentation site it would otherwise store the loading
shell -- text like `"You need to enable JavaScript to run this app."` -- and report
success. The source then silently never matches a query.

For a JS-rendered page, either save it as a PDF and `add --file`, or read it in a
browser and save the text with `add_text_source`. To index anyway, pass `--force`
(CLI) or `force: true` (MCP).

The rules differ by kind, deliberately:

| Check | Files | URLs |
|---|---|---|
| JavaScript shell markers | rejected | rejected |
| No text at all (e.g. a scanned PDF with no text layer) | rejected | rejected |
| Shorter than 200 characters | allowed | rejected |

A short file you explicitly named is a deliberate act; a short *fetch* is nearly
always a failure.

## Labels and Versions

`add_source` accepts an optional `source_label`. Supply one for URLs in particular:
without it the label falls back to the page `<title>`, which on many documentation
sites is a single constant for every page, leaving sources indistinguishable in
`list_sources`.

A product version stamped in the text (e.g. `2026.07.0`) is detected automatically,
stored on the source, and shown in `list_sources` and search results -- useful when
two releases of the same guide are indexed side by side.

## Duplicate Suppression

Search collapses passages that are identical after whitespace and case normalization,
keeping the best-scoring copy and noting where else the passage appears. Two releases
of one guide therefore no longer return the same text twice. Matching is exact after
normalization, so genuinely different passages are never suppressed. Pass
`dedupe=False` to `Searcher.search` to opt out.

## Folder Sync

```bash
agent-knowledge-server sync ~/docs/curated-pdfs
agent-knowledge-server sync ~/notes --pattern "*.md"
```

Reconciles a directory against the index and reports what it did:

- **added** - on disk, not yet indexed
- **updated** - file bytes changed since last index, so re-indexed
- **unchanged** - byte fingerprint matches
- **backfilled** - indexed before fingerprints existed; fingerprint recorded, content
  left alone (use `--reindex-unknown` to re-index instead)
- **missing** - indexed file source whose path no longer exists
- **failed** - indexing raised; the error is on the registry entry

Unlike `import-pdfs`, which re-indexes everything it finds, `sync` only touches what
actually changed.

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
- The URL fetcher does not execute JavaScript; see "Empty-Extraction Guard".
- Mutating operations (`add`, `add-text`, `import-pdfs`, `sync`, `refresh`, `forget`) are serialized with a local file lock at `~/.local/share/agent-knowledge-server/.write.lock` to avoid concurrent write races when multiple agents share one data directory.
