"""Command-line interface for mlget (MVP skeleton)."""

from __future__ import annotations

import json
from pathlib import Path

import click

from . import __version__, resolver
from .cache import CacheDB
from .config import get_cache_dir
from .downloader import (
    Aria2cDownloader,
    Aria2cNotFound,
    find_aria2c,
    python_fallback_download,
)


@click.group()
@click.version_option(__version__)
def main() -> None:
    """mlget - ML package manager with resumable downloads (MVP skeleton)."""
    pass


@main.command()
@click.argument("package_spec", nargs=1)
@click.option(
    "-w",
    "--workers",
    default=8,
    help="Number of connections per download (aria2c split).",
)
@click.option("--out", default=None, help="Output path (defaults to mlget cache dir)")
def install(package_spec: str, workers: int, out: str | None) -> None:
    """Install (download) a package. Example: mlget install torch==2.1.0+cu121"""
    click.echo(f"Requested install: {package_spec}")
    click.echo(f"Workers: {workers}")

    # Resolve spec to URL or local path candidates
    try:
        candidates = resolver.resolve(package_spec)
    except ValueError as e:
        click.echo(f"Resolver error: {e}")
        raise click.Abort()

    url = candidates[0]
    out_dir = Path(out) if out else get_cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    db = CacheDB()
    # Register download
    filename = Path(url).name or "downloaded.file"
    out_path = str(out_dir / filename)
    download_id = db.add_download(url, out_path, status="queued")
    click.echo(f"Download registered (id={download_id}) -> {out_path}")

    # Choose downloader: prefer aria2c when available
    try:
        if find_aria2c():
            click.echo("Using aria2c if available...")
            d = Aria2cDownloader()
            res = d.download(url, out=out_dir, split=workers)
        else:
            raise Aria2cNotFound()
    except Aria2cNotFound:
        click.echo(
            "aria2c not found, falling back to Python downloader (no multi-connection resume)."
        )
        res = python_fallback_download(url, out=out_dir)

    # Update DB based on result
    if res.get("returncode", 1) == 0:
        db.update_download(
            download_id, status="completed", downloaded_bytes=0, total_bytes=0
        )
        # add cache entry
        try:
            db.add_cache_entry(res.get("out_path", out_path))
        except Exception:
            pass
        click.echo(f"Download completed: {res.get('out_path')}")
    else:
        db.update_download(download_id, status="failed")
        click.echo(f"Download failed: {res.get('stderr')}")


@main.command()
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON")
def status(as_json: bool) -> None:
    """Show current and recent download status."""
    db = CacheDB()
    rows = list(db.list_downloads())
    if as_json:
        click.echo(json.dumps(rows, default=str, ensure_ascii=False))
        return

    if not rows:
        click.echo("No downloads recorded.")
        return

    headers = ["id", "url", "out_path", "status", "created_at", "updated_at"]
    col_widths = {
        h: max(len(h), max((len(str(r.get(h, ""))) for r in rows), default=0))
        for h in headers
    }
    header_line = "  ".join(h.ljust(col_widths[h]) for h in headers)
    click.echo(header_line)
    click.echo("-" * len(header_line))
    for r in rows:
        line = "  ".join(str(r.get(h, "")).ljust(col_widths[h]) for h in headers)
        click.echo(line)


@main.group()
def cache() -> None:
    """Cache management commands."""
    pass


@cache.command("list")
@click.option("--long", "long", is_flag=True, default=False, help="Show detailed info")
def cache_list(long: bool) -> None:
    """List cached files."""
    click.echo(f"Listing cache (long={long})")


@cache.command("clear")
@click.option("--package", "package_name", default=None, help="Clear cache for package")
@click.option("--older-than", default=None, help="Clear files older than DAYS (int)")
def cache_clear(package_name: str | None, older_than: str | None) -> None:
    """Clear cache entries."""
    click.echo(f"Clearing cache package={package_name} older-than={older_than}")


if __name__ == "__main__":
    # allow running directly for quick dev testing
    main()
