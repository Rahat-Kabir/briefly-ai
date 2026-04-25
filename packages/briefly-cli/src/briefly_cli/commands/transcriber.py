from __future__ import annotations

import click


@click.group(help="Manage local transcription tools.")
def transcriber() -> None:
    pass


@transcriber.command()
def setup() -> None:
    click.echo("Transcriber setup is not implemented yet.")

