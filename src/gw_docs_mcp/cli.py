from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer

from gw_docs_mcp.config import load_config, save_config, DEFAULT_CONFIG_PATH
from gw_docs_mcp.server import handle_list, handle_reindex

app = typer.Typer(help="gw-docs-mcp — local semantic search over Guidewire PDF docs")


@app.command()
def configure(
    pdf_dir: str = typer.Option(..., "--pdf-dir", help="Directory containing GW PDF files"),
):
    """Set the PDF directory and write config file."""
    cfg = load_config()
    cfg.docs.pdf_dir = pdf_dir
    save_config(cfg, DEFAULT_CONFIG_PATH)
    typer.echo(f"Saved config to {DEFAULT_CONFIG_PATH}")
    typer.echo(f"  pdf_dir = {pdf_dir}")
    typer.echo("Next: run 'gw-docs-mcp index' to index your PDFs.")


@app.command()
def index(
    pdf_dir: Optional[str] = typer.Option(None, "--pdf-dir", help="Override configured PDF directory"),
):
    """Index all PDFs in the configured (or specified) directory."""
    cfg = load_config()
    target = Path(pdf_dir or cfg.docs.pdf_dir).expanduser()
    if not target.exists():
        typer.echo(f"Error: directory not found: {target}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Indexing PDFs in {target} ...")
    result = handle_reindex({"pdf_dir": str(target)}, cfg)
    typer.echo(result)


@app.command()
def status():
    """Show what is currently indexed."""
    cfg = load_config()
    result = handle_list({}, cfg)
    typer.echo(result)


@app.command()
def reset(
    pdf_dir: Optional[str] = typer.Option(None, "--pdf-dir", help="Override configured PDF directory"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Wipe the index and re-index from scratch. Use when PDFs are removed or renamed."""
    import shutil
    cfg = load_config()
    chroma_dir = Path(cfg.chroma.persist_dir).expanduser()

    if not yes:
        typer.confirm(f"This will delete the index at {chroma_dir} and re-index. Continue?", abort=True)

    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        typer.echo(f"Wiped index at {chroma_dir}")

    target = Path(pdf_dir or cfg.docs.pdf_dir).expanduser()
    if not target.exists():
        typer.echo(f"Error: directory not found: {target}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Indexing PDFs in {target} ...")
    result = handle_reindex({"pdf_dir": str(target)}, cfg)
    typer.echo(result)


@app.command()
def serve():
    """Start the MCP server (called by Claude Code automatically)."""
    from gw_docs_mcp.server import main
    main()
