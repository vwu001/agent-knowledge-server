from __future__ import annotations

# Canonical list of MCP tools this server exposes.
#
# Both the server's list_tools() and the installer's Claude permission
# allow-list derive from this, so a newly added tool is pre-approved instead of
# silently prompting on every call. Lives in its own module so the installer can
# read it without importing the heavy indexing stack.
TOOL_NAMES = [
    "add_source",
    "sync_folder",
    "add_text_source",
    "add_text_source_from_context",
    "import_pdf_folder",
    "list_sources",
    "list_documents",
    "search_knowledge",
    "refresh_source",
    "forget_source",
]
