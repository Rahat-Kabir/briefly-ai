from __future__ import annotations

import click

from briefly_core.cache import clear_cache, get_cache_stats


@click.group(help="Inspect or clear Briefly cache.")
def cache() -> None:
    pass


@cache.command()
def stats() -> None:
    cache_stats = get_cache_stats()
    if cache_stats.path is None:
        raise click.ClickException("Could not resolve cache path. Set BRIEFLY_CONFIG.")

    click.echo(f"Cache: {cache_stats.path}")
    click.echo(f"Exists: {'yes' if cache_stats.exists else 'no'}")
    click.echo(f"URL entries: {cache_stats.url_entries}")
    click.echo(f"Summary entries: {cache_stats.summary_entries}")
    click.echo(f"Size: {_format_bytes(cache_stats.size_bytes)}")


@cache.command()
def clear() -> None:
    cleared = clear_cache()
    if cleared.path is None:
        raise click.ClickException("Could not resolve cache path. Set BRIEFLY_CONFIG.")

    click.echo(f"Cleared cache: {cleared.path}")
    click.echo(f"URL entries removed: {cleared.url_entries}")
    click.echo(f"Summary entries removed: {cleared.summary_entries}")


def _format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes / 1024:.1f} KB"
