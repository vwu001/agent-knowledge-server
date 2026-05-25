# agent-knowledge-server Design Spec
Draft 1.0 | 2026-05-25

## Summary

`agent-knowledge-server` is a agent knowledge server for explicitly curated sources. A source is exactly one local file path or one URL. The system indexes only what the user deliberately adds, then provides semantic search, source listing, source refresh, and source forgetting over a agent knowledge base.

This is a hard reset from `gw-docs-mcp`, not a compatibility-preserving rename. The new product is generic by default and designed to grow from PDF-only ingestion into a broader personal wiki-style retrieval system for files and web pages.

---

## 1. Goals

- Replace Guidewire-specific branding and contracts with a generic agent knowledge product
- Support explicit single-source ingestion for both local files and URLs
- Keep indexing intentional and low-noise by disallowing folder ingestion and auto-crawling
- Preserve local-first operation with no required cloud services after dependency installation
- Add source lifecycle controls: add, list, refresh, forget
- Begin evolving from document search into a wiki-like knowledge base with richer metadata and browsing

---

## 2. Non-Goals

- No folder indexing in v2
- No recursive web crawling or link following in v2
- No background watcher or automatic refresh in v2
- No remote hosted service or multi-user deployment in v2
- No OCR pipeline in v2
- No compatibility aliases for old GW package names, tool names, storage paths, or config paths

---

## 3. Product Model

### 3.1 Source

A source is one explicit user-managed input:

- one local file path, or
- one URL

Each source becomes a first-class record in the registry and is the unit of indexing, refresh, inspection, and deletion.

### 3.2 Supported Source Kinds

Initial source kinds:

- local file
- URL

Initial file/content types:

- PDF
- Markdown
- plain text
- HTML
- DOCX if practical in the first implementation slice

If DOCX support adds too much churn to the first slice, the architecture should still reserve a loader boundary for it and defer the actual loader to a follow-up task.

### 3.3 Intentional Curation

The system will not accept folder paths and will not follow links from a URL. Users add sources one at a time. This keeps the index small, understandable, and less likely to be polluted by irrelevant content.

---

## 4. Core User Actions

The system should support these core actions as first-class CLI commands and MCP tools:

- add a single local file
- add a single URL
- list sources
- search indexed knowledge
- list normalized documents or sections derived from sources
- refresh one source
- forget one source

The mental model is:

1. Add a trusted source.
2. The system indexes it into the agent knowledge base.
3. Search and inspect what is in the knowledge base.
4. Refresh or forget sources deliberately.

---

## 5. Command and Tool Surface

This is a hard rename. The new surface should be generic only.

### 5.1 CLI

Recommended commands:

- `agent-knowledge-server add --file /path/to/doc.pdf`
- `agent-knowledge-server add --url https://example.com/page`
- `agent-knowledge-server list-sources`
- `agent-knowledge-server list-documents`
- `agent-knowledge-server search "query text"`
- `agent-knowledge-server refresh --source-id <id>`
- `agent-knowledge-server forget --source-id <id>`
- `agent-knowledge-server status`
- `agent-knowledge-server serve`

Possible optional variants:

- `agent-knowledge-server add /path/to/file`
- `agent-knowledge-server add https://example.com/page`

The explicit `--file` and `--url` flags are safer and easier to validate in early versions, so they are the recommended starting contract.

### 5.2 MCP Tools

Recommended tool set:

- `add_source`
- `list_sources`
- `list_documents`
- `search_knowledge`
- `refresh_source`
- `forget_source`

Suggested tool behavior:

- `add_source`
  - accepts either `file_path` or `url`
  - rejects calls that provide both or neither
  - creates or updates the source record
  - indexes the source immediately
- `list_sources`
  - returns tracked sources with type, title, status, last indexed time, and source id
- `list_documents`
  - returns normalized documents or sections with source linkage
- `search_knowledge`
  - searches across all indexed chunks and returns source attribution
- `refresh_source`
  - fully reindexes one source
- `forget_source`
  - deletes the source registry record, URL snapshot if applicable, and all indexed chunks for that source

---

## 6. Storage Layout

### 6.1 Configuration

Store configuration at:

- `~/.config/agent-knowledge-server/config.toml`

This file should contain user settings such as:

- embedding model
- search defaults
- application data paths if overridden

### 6.2 App Data

Store app-owned data at:

- `~/.local/share/agent-knowledge-server/`

Suggested layout:

```text
~/.local/share/agent-knowledge-server/
  sources/
    registry.json
    <source-id>/
      metadata.json
      snapshot.html
      snapshot.txt
  chroma/
  models/
```

### 6.3 Local Files

Local file sources should store:

- the original file path
- inferred content type
- title if available
- fingerprint or hash for change detection

The file contents should not be copied into app storage. The indexer re-reads the file from its original path during refresh or reindex.

### 6.4 URLs

URL sources should store:

- original URL
- fetched timestamp
- response content type
- title if extracted
- fingerprint or hash of normalized content
- a normalized snapshot file under the source directory

URL snapshots are app-owned and should be removed by `forget_source`.

---

## 7. Data Model

### 7.1 Source Record

Each source record should include at least:

- `source_id`
- `kind`: `file` or `url`
- `original`
- `content_type`
- `title`
- `status`: `pending`, `indexed`, `failed`, `stale`
- `created_at`
- `updated_at`
- `last_indexed_at`
- `fingerprint`
- `error`

### 7.2 Normalized Document

Each source may produce one or more normalized documents or sections. These should capture:

- `document_id`
- `source_id`
- `title`
- `section_path` or heading path
- `content`
- source-specific metadata such as page number or heading

### 7.3 Chunk Metadata

Each embedded chunk should include enough metadata for search result attribution and targeted deletion:

- `chunk_id`
- `source_id`
- `document_id`
- `source_title`
- `source_kind`
- `content_type`
- `page` for PDFs where applicable
- `section_path` where applicable

The critical change from the current repo is that chunk ownership must be keyed by `source_id`, not just filename, so `forget_source` can reliably delete exactly one source’s content.

---

## 8. Ingestion Pipeline

### 8.1 Loader Boundary

The current implementation is PDF-specific in the loader, but generic in the embedding and search layers. The new system should keep one shared downstream pipeline and move format logic into loaders.

Recommended flow:

1. Resolve source input.
2. Infer source kind and content type.
3. Run the appropriate loader.
4. Produce normalized document records.
5. Chunk normalized document text.
6. Embed chunks.
7. Upsert chunks into Chroma with source-aware metadata.
8. Update the source registry status and metadata.

### 8.2 Initial Loaders

Recommended first loaders:

- PDF loader
- Markdown loader
- plain text loader
- HTML loader for both local HTML files and fetched web pages

Optional in first slice:

- DOCX loader

### 8.3 URL Fetching

When adding a URL:

1. Fetch only the exact URL.
2. Do not follow links for indexing.
3. Normalize the content into indexable text.
4. Save a stable snapshot into app storage.
5. Index from the normalized snapshot result.

Refreshing a URL repeats the fetch and replaces the old snapshot and chunks for that source.

---

## 9. Search and Wiki-Like Behavior

The first version remains retrieval-first, but should lay groundwork for wiki-like browsing.

### 9.1 Search

Search results should include:

- source title or identifier
- source type
- original path or URL
- page or section metadata when available
- snippet text
- similarity score

### 9.2 Listing and Inspection

`list_sources` is the top-level library view.

`list_documents` is the derived content view. It begins to make the system feel more wiki-like by exposing what documents and sections exist inside each source rather than only raw chunk counts.

### 9.3 Future Wiki Extensions

Out of scope for the first implementation, but enabled by this design:

- section-level browsing
- source summaries
- extracted heading trees
- tag or topic metadata
- related-source suggestions
- backlinks or semantic nearest-neighbor relationships between documents

---

## 10. Rename and Migration

This project should perform a hard reset rename:

- package name changes from `gw-docs-mcp` to `agent-knowledge-server`
- Python module path changes away from `gw_docs_mcp`
- CLI binary changes to `agent-knowledge-server`
- config path changes away from `~/.config/gw-docs-mcp/`
- storage paths change away from `~/.gw-docs-mcp/`
- MCP server name and tool names change to generic names
- README and plugin metadata are fully rewritten

No compatibility alias layer should be added in this pass.

---

## 11. Error Handling

- Reject folder paths in `add_source`
- Reject `add_source` calls with both `file_path` and `url`
- Reject `add_source` calls with neither input
- Return clear errors for unsupported file types
- Mark sources as `failed` with stored error context when indexing fails
- Surface missing local file errors in `refresh_source`
- Surface URL fetch failures with response details when practical
- Ensure `forget_source` is safe and idempotent even if the source is already partly removed

---

## 12. Testing

The test suite should shift from GW-flavored fixtures toward generic knowledge-source fixtures.

Recommended coverage:

- source registry create, update, list, delete
- file source add for PDF, Markdown, text, and HTML
- URL source add with snapshot persistence
- refresh semantics for both file and URL sources
- `forget_source` deleting only one source’s chunks
- search results carrying source metadata
- `list_documents` returning normalized document records
- CLI argument validation
- MCP tool validation and formatting

Integration tests should continue to allow a real embedding-model path, but the main suite should remain fast with mocked embeddings.

---

## 13. Implementation Slice Recommendation

The smallest correct first implementation slice is:

1. hard rename to `agent-knowledge-server`
2. introduce a persistent source registry
3. support explicit file and URL sources
4. keep PDF support working
5. add Markdown, text, and HTML loaders
6. add URL snapshot storage
7. add `add_source`, `list_sources`, `forget_source`, and `refresh_source`
8. add `list_documents`
9. update tests and docs to generic wording

DOCX support can be included only if it fits cleanly after these steps without destabilizing the core architecture.

---

## 14. Open Implementation Notes

- The current Chroma metadata model is too thin for source lifecycle management and must be expanded.
- The current indexer only scans `*.pdf` in a directory and should be replaced by single-source ingestion entry points.
- The current CLI `configure` command centered on one PDF directory should be removed or repurposed because explicit source management replaces directory-based indexing.
- The current storage split should be simplified so app-owned mutable data lives together under `~/.local/share/agent-knowledge-server/`.

---

## 15. Decision Summary

Approved decisions captured in this spec:

- hard reset rename to `agent-knowledge-server`
- no GW compatibility layer
- explicit single-source ingestion only
- no folder indexing
- local files are remembered by path and not copied
- URLs are snapshotted into app-owned storage
- URL ingestion indexes only the exact URL and does not crawl
- core actions are add, list, search, list documents, refresh, and forget
