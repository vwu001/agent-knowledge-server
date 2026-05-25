from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from agent_knowledge_server.config import AgentKnowledgeConfig, load_config
from agent_knowledge_server.indexer import Indexer
from agent_knowledge_server.searcher import Searcher

_server = Server("agent-knowledge")


def handle_add(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    indexer = Indexer(cfg)
    file_path = arguments.get("file_path")
    url = arguments.get("url")
    if bool(file_path) == bool(url):
        return "Provide exactly one of file_path or url."
    if file_path:
        source = indexer.add_file_source(Path(file_path))
    else:
        source = indexer.add_url_source(url)
    return f"Indexed source '{source.title or source.original}' with source_id={source.source_id}"


def handle_add_text_source(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    content = arguments.get("content", "").strip()
    source_label = arguments.get("source_label", "").strip()
    if not content or not source_label:
        return "Provide both content and source_label."
    source = Indexer(cfg).add_text_source(
        content=content,
        source_label=source_label,
        title=arguments.get("title"),
        source_kind=arguments.get("source_kind"),
        original_ref=arguments.get("original_ref"),
        notes=arguments.get("notes"),
    )
    return f"Indexed source '{source.title or source.source_label or source.original}' with source_id={source.source_id}"


def handle_import_pdf_folder(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    folder = arguments.get("dir")
    pattern = arguments.get("pattern", "*.pdf")
    if not folder:
        return "Provide dir for PDF import."
    imported = Indexer(cfg).import_pdf_folder(Path(folder), pattern=pattern)
    if not imported:
        return f"No PDFs found in {folder}"
    return f"Imported {len(imported)} PDF source(s) from {folder}"


def handle_list_sources(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    sources = Searcher(cfg).list_sources()
    if not sources:
        return "No sources indexed yet."
    lines = [f"{'Source ID':<18} {'Kind':<6} {'Status':<8} Label"]
    lines.append("-" * 72)
    for source in sources:
        label = source.source_label or source.title or source.original
        lines.append(f"{source.source_id:<18} {source.kind:<6} {source.status:<8} {label}")
    return "\n".join(lines)


def handle_list_documents(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    documents = Searcher(cfg).list_documents()
    if not documents:
        return "No documents indexed yet."
    lines = [f"{'Source ID':<18} {'Document ID':<24} Title"]
    lines.append("-" * 72)
    for document in documents:
        lines.append(f"{document['source_id']:<18} {document['document_id']:<24} {document['title']}")
    return "\n".join(lines)


def handle_search(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    query = arguments["query"]
    top_k = arguments.get("top_k", cfg.search.top_k)
    results = Searcher(cfg).search(query, top_k=top_k)
    if not results:
        return "No indexed content yet."
    lines = []
    for idx, result in enumerate(results, 1):
        page = f" p.{result.page}" if result.page else ""
        lines.append(f"[{idx}] {result.title}{page} (score: {result.score})")
        lines.append(result.text)
        lines.append("")
    return "\n".join(lines).strip()


def handle_refresh(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    source_id = arguments["source_id"]
    source = Indexer(cfg).refresh_source(source_id)
    return f"Refreshed source_id={source.source_id}"


def handle_forget(arguments: dict[str, Any], cfg: AgentKnowledgeConfig) -> str:
    searcher = Searcher(cfg)
    source_id = arguments.get("source_id")
    if source_id:
        Indexer(cfg).forget_source(source_id)
        return f"Forgot source_id={source_id}"

    candidates = []
    for key in ("source_label", "original_ref", "fuzzy_target"):
        target = arguments.get(key)
        if target:
            candidates = searcher.find_sources(target)
            break

    if not candidates:
        return "No matching source found to forget."
    if len(candidates) > 1:
        labels = ", ".join(f"{item.source_id} ({item.source_label or item.title or item.original})" for item in candidates)
        return f"Multiple matching sources found: {labels}"

    source = candidates[0]
    Indexer(cfg).forget_source(source.source_id)
    return f"Forgot source_id={source.source_id}"


@_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="add_source",
            description="Add and index one local file path or one URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
        ),
        Tool(
            name="add_text_source",
            description="Add normalized text content provided by the LLM or user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "source_label": {"type": "string"},
                    "title": {"type": "string"},
                    "source_kind": {"type": "string"},
                    "original_ref": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["content", "source_label"],
            },
        ),
        Tool(
            name="add_text_source_from_context",
            description="Add normalized text derived from current assistant context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "source_label": {"type": "string"},
                    "title": {"type": "string"},
                    "source_kind": {"type": "string"},
                    "original_ref": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["content", "source_label"],
            },
        ),
        Tool(
            name="import_pdf_folder",
            description="Batch import a curated folder of PDFs as individual file sources.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dir": {"type": "string"},
                    "pattern": {"type": "string"},
                },
                "required": ["dir"],
            },
        ),
        Tool(name="list_sources", description="List indexed sources.", inputSchema={"type": "object", "properties": {}}),
        Tool(
            name="list_documents",
            description="List normalized documents derived from indexed sources.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="search_knowledge",
            description="Search indexed knowledge.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="refresh_source",
            description="Refresh one indexed source.",
            inputSchema={
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
        ),
        Tool(
            name="forget_source",
            description="Forget one indexed source and delete its indexed chunks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "source_label": {"type": "string"},
                    "original_ref": {"type": "string"},
                    "fuzzy_target": {"type": "string"},
                },
            },
        ),
    ]


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    cfg = load_config()
    if name == "add_source":
        text = handle_add(arguments, cfg)
    elif name in {"add_text_source", "add_text_source_from_context"}:
        text = handle_add_text_source(arguments, cfg)
    elif name == "import_pdf_folder":
        text = handle_import_pdf_folder(arguments, cfg)
    elif name == "list_sources":
        text = handle_list_sources(arguments, cfg)
    elif name == "list_documents":
        text = handle_list_documents(arguments, cfg)
    elif name == "search_knowledge":
        text = handle_search(arguments, cfg)
    elif name == "refresh_source":
        text = handle_refresh(arguments, cfg)
    elif name == "forget_source":
        text = handle_forget(arguments, cfg)
    else:
        text = f"Unknown tool: {name}"
    return [TextContent(type="text", text=text)]


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(read_stream, write_stream, _server.create_initialization_options())


def main() -> None:
    asyncio.run(_main())
