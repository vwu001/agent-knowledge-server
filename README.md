# agent-knowledge-server

Curated agent knowledge server for coding agents. Add one file path or one URL at a time, or let the assistant save normalized text directly, then search, list, refresh, or forget that knowledge.

## Install

Three supported paths. Pick the one that matches your situation; they install the
same skill and the same MCP server.

### Path A — Claude Code plugin

One step, and it registers the skill and the MCP server together. Nothing to edit
by hand.

```bash
/plugin marketplace add vwu001/agent-knowledge-server
```

```bash
/plugin install agent-knowledge-server
```

The plugin still needs the `agent-knowledge-server` command on your PATH, because
that is what the MCP server runs. Install it with Path B's first command if you do
not have it yet.

### Path B — pip / uv (Codex, or manual Claude setup)

```bash
uv tool install git+https://github.com/vwu001/agent-knowledge-server.git
```

```bash
agent-knowledge-server install
```

`uv` is recommended over `pip` for one specific reason: Homebrew and system Pythons
are marked externally managed (PEP 668) and will **refuse** a global `pip install`
outright. `uv tool install` sidesteps that by giving the package its own isolated
environment and putting just the command on your PATH. If you prefer pip, install
into a virtualenv you control:

```bash
pip install git+https://github.com/vwu001/agent-knowledge-server.git
```

`agent-knowledge-server install` installs the global assistant skill, writes the
Codex MCP config, updates Claude MCP tool permissions, and attempts Claude MCP
registration.

Codex uses `~/.codex/config.toml` for MCP setup, not `settings.json`. The installer
writes:

```toml
[mcp_servers.agent-knowledge]
command = "agent-knowledge-server"
args = ["serve"]
default_tools_approval_mode = "approve"
```

Claude uses `~/.claude/settings.json` for tool permissions. The installer adds every
`mcp__agent-knowledge__...` tool to `permissions.allow`.

### Path C — from a clone or a downloaded ZIP

If you already have the source on disk, install from the directory instead of the
git URL. Both cases are the same once you are inside the folder.

Downloaded a ZIP? Unzip it and note that GitHub names the folder after the branch:

```bash
cd agent-knowledge-server-main
```

Then, for a clone or a ZIP alike:

```bash
uv tool install .
```

```bash
agent-knowledge-server install
```

No git metadata is required — the version is static in `pyproject.toml`, so a ZIP
with no `.git` directory builds exactly like a clone.

To use the Claude plugin from a local checkout, point the marketplace at the
directory rather than the GitHub slug:

```bash
/plugin marketplace add /full/path/to/agent-knowledge-server
```

**Contributors:** use `uv tool install -e .` so your edits take effect without
reinstalling, while the command stays on your PATH.

**Avoid a plain virtualenv.** `python -m venv .venv && pip install -e .` is the
obvious move, and it half-works in a confusing way: the CLI runs fine in your
activated shell, but your assistant launches the MCP server as a subprocess with
your normal PATH, where `<venv>/bin` does not appear. The CLI looks healthy while
MCP silently fails to connect. The installer now detects this and writes the venv's
absolute path into the MCP config instead, printing a notice — but `uv tool install`
avoids the problem outright.

**After `git pull`,** re-run `uv tool install . --reinstall` to pick up the changes,
unless you installed with `-e`.

## Verify It Worked

**Restart your assistant session first.** MCP servers and skills are loaded at
session start, so a fresh install is invisible to the session that ran it. This is
the single most common reason people think the install failed.

Then check all three layers:

```bash
agent-knowledge-server list-sources
```

1. **Command** — the above runs and prints `Sources: 0` rather than "command not found".
2. **MCP** — run `/mcp` in Claude Code and confirm `agent-knowledge` is listed and
   connected. In Codex, confirm the `[mcp_servers.agent-knowledge]` block is in
   `~/.codex/config.toml`.
3. **Skill** — ask your assistant "search my agent knowledge for anything". It should
   reach for the `search_knowledge` tool without being told the tool name.

### If something is missing

| Symptom | Cause | Fix |
|---|---|---|
| `command not found` | The install directory is not on your PATH | `uv tool update-shell`, then open a new terminal |
| `pip` refuses with "externally-managed-environment" | PEP 668 on a Homebrew/system Python | Use `uv tool install`, or a virtualenv |
| MCP tools missing after install | Session not restarted | Start a new session |
| CLI works but MCP will not connect | Installed into an unactivated virtualenv | Re-run `agent-knowledge-server install`, or reinstall with `uv tool install .` |
| MCP listed but every call asks permission | `permissions.allow` not applied | Re-run `agent-knowledge-server install --mcp-only` |
| First search is slow or times out | The embedding model downloads on first use | Run one `search` from the CLI to warm it |

## Using It In A Dev Session

The value is in answering what the repo alone cannot — vendor behaviour, config
semantics, upgrade notes. Load the docs once:

```bash
agent-knowledge-server sync ~/docs/product-guides --pattern "*.pdf"
```

Then in an assistant session, ask questions that span both:

> "Our `ProductEditionPlugin` override returns the wrong edition for backdated
> changes. What does the product docs say the default resolution order is, and where
> does our implementation diverge?"

The assistant searches the indexed docs, reads the repo, and reports the gap between
them. Search results carry the `source_label` and detected version, so you can tell
whether the doc actually applied to your release.

If the corporate tenant blocks downloading a SharePoint library, sync it to OneDrive
and point `sync_folder` at the local sync path — the bundled skill walks your
assistant through this.

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
