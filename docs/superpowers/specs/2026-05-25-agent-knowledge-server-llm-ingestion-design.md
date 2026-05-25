# agent-knowledge-server LLM Ingestion Design
Draft 1.0 | 2026-05-25

## Summary

Add MCP-first LLM-assisted ingestion to `agent-knowledge-server` so Codex can extract or normalize content from whatever it already has access to, then store that content directly in the agent knowledge base without requiring a dedicated parser or connector for each source type.

This extends the current explicit file/URL model with direct text ingestion and more natural forgetting behavior.

## Approved Decisions

- The MCP server should accept both `content` and `source_label`
- LLM-assisted ingestion should live in MCP tools, not only in a Codex skill
- The existing file/URL tools remain useful and should coexist with text-first ingestion
- Forgetting should support natural human-oriented targets, not only exact `source_id`
- If removal is ambiguous, the server should refuse to guess and return a disambiguation message

## New MCP Tool Surface

- `add_text_source`
- `add_text_source_from_context`
- `forget_source` extended with fuzzy matching inputs

## Data Contract

`add_text_source` and `add_text_source_from_context` should accept:

- `content` required
- `source_label` required
- `title` optional
- `source_kind` optional
- `original_ref` optional
- `notes` optional

The indexed source should be persisted as a first-class source record, similar to file and URL sources, with the text stored as app-owned source content.

## Forget Behavior

`forget_source` should resolve in this order:

1. exact `source_id`
2. exact `source_label`
3. exact `original_ref`
4. fuzzy match on source label, title, and original ref

If exactly one match is found, forget it.

If no matches are found, return a clear failure message.

If more than one match is found, return an ambiguity message listing candidate sources.

## Codex Guidance

`AGENTS.md` should teach Codex:

- when user says to save useful knowledge from accessible content, normalize it and call `add_text_source`
- when user says something is wrong and should be forgotten, call `forget_source` using the best available current target context

## Scope

This pass does not add external connectors. It adds a storage contract that lets Codex bring its own extracted text into the knowledge base.
