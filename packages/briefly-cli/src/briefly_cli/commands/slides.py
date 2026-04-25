from __future__ import annotations

import click


@click.group(help="Extract or brief slides from a video.")
def slides() -> None:
    pass


@slides.command("run", hidden=True)
@click.argument("url", required=False)
def run(url: str | None = None) -> None:
    _ = url
    click.echo("Slides are not implemented yet.")
