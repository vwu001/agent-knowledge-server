from __future__ import annotations

from pathlib import Path

import typer

from local_knowledge_mcp.config import load_config
from local_knowledge_mcp.installer import install_everything
from local_knowledge_mcp.indexer import Indexer
from local_knowledge_mcp.searcher import Searcher
from local_knowledge_mcp.server import (
    handle_add,
    handle_forget,
    handle_list_documents,
    handle_list_sources,
    handle_refresh,
    handle_search,
)

app = typer.Typer(help="local-knowledge-mcp - local knowledge indexing for explicit file and URL sources")


@app.command("add")
def add(
    file: str | None = typer.Option(None, "--file", help="Single local file to index"),
    url: str | None = typer.Option(None, "--url", help="Single URL to fetch and index"),
):
    cfg = load_config()
    text = handle_add({"file_path": file, "url": url}, cfg)
    if text.startswith("Provide exactly one"):
        typer.echo(text, err=True)
        raise typer.Exit(1)
    typer.echo(text)


@app.command("add-text")
def add_text(
    source_label: str = typer.Option(..., "--source-label", help="Human-readable label"),
    content: str = typer.Option(..., "--content", help="Normalized text content to index"),
    title: str | None = typer.Option(None, "--title", help="Optional title"),
    source_kind: str | None = typer.Option(None, "--source-kind", help="Optional kind hint"),
    original_ref: str | None = typer.Option(None, "--original-ref", help="Optional original reference"),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
):
    from local_knowledge_mcp.server import handle_add_text_source

    typer.echo(
        handle_add_text_source(
            {
                "source_label": source_label,
                "content": content,
                "title": title,
                "source_kind": source_kind,
                "original_ref": original_ref,
                "notes": notes,
            },
            load_config(),
        )
    )


@app.command("list-sources")
def list_sources():
    typer.echo(handle_list_sources({}, load_config()))


@app.command("list-documents")
def list_documents():
    typer.echo(handle_list_documents({}, load_config()))


@app.command("search")
def search(query: str, top_k: int | None = typer.Option(None, "--top-k", help="Number of results")):
    typer.echo(handle_search({"query": query, "top_k": top_k}, load_config()))


@app.command("refresh")
def refresh(source_id: str = typer.Option(..., "--source-id", help="Source identifier")):
    typer.echo(handle_refresh({"source_id": source_id}, load_config()))


@app.command("forget")
def forget(
    source_id: str | None = typer.Option(None, "--source-id", help="Source identifier"),
    target: str | None = typer.Option(None, "--target", help="Human-readable target to forget"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    if not source_id and not target:
        typer.echo("Provide either --source-id or --target.", err=True)
        raise typer.Exit(1)
    if not yes:
        typer.confirm(f"Forget source {source_id or target} and delete its indexed chunks?", abort=True)
    payload = {"source_id": source_id, "fuzzy_target": target}
    typer.echo(handle_forget(payload, load_config()))


@app.command("status")
def status():
    cfg = load_config()
    searcher = Searcher(cfg)
    sources = searcher.list_sources()
    documents = searcher.list_documents()
    typer.echo(f"Sources: {len(sources)}")
    typer.echo(f"Documents: {len(documents)}")


@app.command("install")
def install(
    mcp_only: bool = typer.Option(False, "--mcp-only", help="Install only MCP registration"),
    skill_only: bool = typer.Option(False, "--skill-only", help="Install only the global skill"),
    codex: bool = typer.Option(False, "--codex", help="Target Codex only"),
    claude: bool = typer.Option(False, "--claude", help="Target Claude only"),
):
    if mcp_only and skill_only:
        typer.echo("Choose either --mcp-only or --skill-only, not both.", err=True)
        raise typer.Exit(1)

    install_skill = not mcp_only
    install_mcp = not skill_only
    messages = install_everything(
        install_skill=install_skill,
        install_mcp=install_mcp,
        codex=codex,
        claude=claude,
    )
    for message in messages:
        typer.echo(message)


@app.command("serve")
def serve():
    from local_knowledge_mcp.server import main

    main()
