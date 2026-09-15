---
name: agent-knowledge-server
description: Use when a user wants to save useful content to agent knowledge, search saved knowledge, or forget incorrect saved knowledge
---

# agent-knowledge-server

Use this skill when the user wants to interact with the agent knowledge MCP.

## Setup

- Install or refresh the skill and MCP registration with `agent-knowledge-server install`.
- After installation, start a new assistant session before relying on the MCP tools.
- The installer is expected to write the MCP config and Claude permissions for you.
- If Codex or Claude can see this skill but the MCP tools are missing or still prompting too much, inspect the local MCP config before doing knowledge work.

### Codex Setup

- Codex uses `~/.codex/config.toml`, not `settings.json`, for MCP registration and approval defaults.
- `agent-knowledge-server install` should ensure `~/.codex/config.toml` contains:

```toml
[mcp_servers.agent-knowledge]
command = "agent-knowledge-server"
args = ["serve"]
default_tools_approval_mode = "approve"
```

- If you prefer tighter control, keep `default_tools_approval_mode = "prompt"` and set per-tool approval overrides instead.

### Claude Setup

- `agent-knowledge-server install` should register the Claude MCP server and update `~/.claude/settings.json`.
- The `permissions.allow` array should include:

```json
[
  "mcp__agent-knowledge__add_source",
  "mcp__agent-knowledge__sync_folder",
  "mcp__agent-knowledge__add_text_source",
  "mcp__agent-knowledge__add_text_source_from_context",
  "mcp__agent-knowledge__import_pdf_folder",
  "mcp__agent-knowledge__list_sources",
  "mcp__agent-knowledge__list_documents",
  "mcp__agent-knowledge__search_knowledge",
  "mcp__agent-knowledge__refresh_source",
  "mcp__agent-knowledge__forget_source"
]
```

## Save Knowledge

- If the user wants to save useful knowledge from accessible content, normalize the content first.
- Prefer `add_text_source` for LLM-derived content provided by the user.
- Prefer `add_text_source_from_context` when the content is derived from the current assistant conversation context.
- Prefer `add_source` for a single explicit file path or URL.
- Prefer `import_pdf_folder` for a curated folder of PDFs that should become individual sources.
- Prefer `sync_folder` when a directory is the source of truth and you want to add new files and
  re-index changed ones without touching the rest.
- Include a human-readable `source_label` whenever possible — `add_source` accepts one too.
  This matters most for URLs: with no label the source is named after the page `<title>`, and many
  documentation sites use one constant title for every page, which makes sources indistinguishable.

### If add_source refuses

`add_source` returns `Refused to index: ...` when nothing usable came out of the source. The
common cause is a JavaScript-rendered page: the fetcher does not run JavaScript, so it only sees
the loading shell. Do not just retry, and do not reach for `force` as the first move — it indexes
the useless shell. Instead:

- save the page as a PDF and add the file, or
- read the page (browser/other tooling) and save the text with `add_text_source`, setting
  `original_ref` to the page URL so provenance survives.

Use `force: true` only when you have inspected the content and know the short text is genuinely
what you want.

## Ingesting Org Documents (SharePoint / Confluence-backed folders)

Many corporate tenants block bulk download of a SharePoint or Teams document library, so there is
no folder on disk to hand to `sync_folder` or `import_pdf_folder`. Do not fight the download
button. Walk the user through OneDrive sync instead:

1. In the browser, open the SharePoint or Teams document library, then choose **Sync** (not
   "Download"). This is usually permitted where download is not.
2. Wait for OneDrive to finish. Then locate the local sync path:
   - macOS: `~/Library/CloudStorage/OneDrive-<OrgName>/<Library>` (older clients: `~/OneDrive - <OrgName>/...`)
   - Windows: `%USERPROFILE%\OneDrive - <OrgName>\<Library>`
3. Confirm the files are real, not placeholders. Files-On-Demand leaves 0-byte stubs that extract
   to nothing and get refused as empty. In Finder/Explorer choose **Always keep on this device**
   for the folder, then check sizes are non-zero before indexing.
4. Hand that local path to `sync_folder`. Use a `source_label` naming the library and, where the
   docs are versioned, the release.

When the library changes upstream, OneDrive updates the local copy — re-run `sync_folder` on the
same path. It adds new files and re-indexes changed ones without disturbing the rest.

If only a handful of documents matter, it is faster to skip sync entirely: have the user open each
page and use `add_text_source` with `original_ref` set to the SharePoint URL.

## Using Knowledge Alongside Code

The point of this server is answering questions the repo alone cannot answer — vendor behaviour,
config semantics, upgrade notes. In a development session:

- **Search before proposing.** When a task touches a documented product or API, run
  `search_knowledge` before reading code, then reconcile what the docs say with what the repo does.
  The gap between them is usually the actual answer.
- **Cite what you used.** Name the `source_label` and version in your answer so the user can judge
  whether the doc applied to their environment.
- **Trust the repo over the docs on local behaviour**, and say so when they disagree — a customised
  implementation often diverges from the vendor default.
- **Capture what the session established.** When the user confirms a non-obvious conclusion that
  is not written down anywhere, offer `add_text_source_from_context` to save it with a clear
  `source_label`. Offer; do not save silently.
- **Retire what is wrong.** When a source is superseded, use `forget_source` rather than leaving
  two versions to compete in search results.

## Search Knowledge

- Use `search_knowledge` to find previously saved information.
- Use `list_sources` or `list_documents` when the user wants to inspect what is stored.
- `list_sources` shows each source's status, detected version, and — for anything not `indexed` —
  the error. A source with `status: empty` holds no usable text and will never match a query;
  re-add it properly or forget it.
- Results carry the detected product version where one was found, and note when the same passage
  also appears in another source (typically two releases of one guide). Prefer the version that
  matches the environment being asked about, not simply the newest.

## Refresh Knowledge

- Use `refresh_source` when a source is stale or the user wants to re-index it from its original location.
- Requires `source_id`; use `list_sources` first if the id is unknown.

## Remove Wrong Knowledge

- If the user says content is wrong, stale, or should be removed, use `forget_source`.
- Prefer a natural target or label when possible, not only source ids.
