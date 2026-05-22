from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from gw_docs_mcp.config import GwDocsConfig, load_config
from gw_docs_mcp.indexer import Indexer
from gw_docs_mcp.searcher import Searcher

_server = Server("gw-docs")


def handle_search(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    query = arguments["query"]
    top_k = arguments.get("top_k", cfg.search.top_k)
    searcher = Searcher(cfg)
    results = searcher.search(query, top_k=top_k)
    if not results:
        return "No documents indexed yet. Run: gw-docs-mcp index"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.source} p.{r.page + 1} (score: {r.score})")
        lines.append(r.text)
        lines.append("")
    return "\n".join(lines).strip()


def handle_list(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    searcher = Searcher(cfg)
    docs = searcher.list_docs()
    if not docs:
        return "No documents indexed yet. Run: gw-docs-mcp index"
    lines = [f"{'Source':<40} {'Chunks':>6}"]
    lines.append("-" * 48)
    for d in docs:
        lines.append(f"{d['source']:<40} {d['chunks']:>6} chunks")
    return "\n".join(lines)


def handle_reindex(arguments: dict[str, Any], cfg: GwDocsConfig) -> str:
    pdf_dir = Path(arguments.get("pdf_dir") or cfg.docs.pdf_dir).expanduser()
    if not pdf_dir.exists():
        return f"PDF directory not found: {pdf_dir}"
    indexer = Indexer(cfg)
    results = indexer.index_directory(pdf_dir)
    if not results:
        return f"No PDFs found in {pdf_dir}"
    lines = [f"Indexed {len(results)} file(s):"]
    for name, count in results.items():
        lines.append(f"  {name}: {count} chunks")
    return "\n".join(lines)


@_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_gw_docs",
            description="Semantically search indexed Guidewire PDF documentation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_gw_docs",
            description="List all indexed Guidewire PDFs and their chunk counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="reindex_gw_docs",
            description="Re-index GW PDFs from the configured directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_dir": {"type": "string", "description": "Override PDF directory path"},
                },
            },
        ),
    ]


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    cfg = load_config()
    if name == "search_gw_docs":
        text = handle_search(arguments, cfg)
    elif name == "list_gw_docs":
        text = handle_list(arguments, cfg)
    elif name == "reindex_gw_docs":
        text = handle_reindex(arguments, cfg)
    else:
        text = f"Unknown tool: {name}"
    return [TextContent(type="text", text=text)]


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_main())
