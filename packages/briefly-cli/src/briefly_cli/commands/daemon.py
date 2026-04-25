from __future__ import annotations

import click


@click.group(help="Manage the local Briefly daemon.")
def daemon() -> None:
    pass


@daemon.command()
@click.option("--host", default="127.0.0.1", help="Daemon host.")
@click.option("--port", default=8788, type=int, help="Daemon port.")
def run(host: str, port: int) -> None:
    _ = (host, port)
    click.echo("Daemon is not implemented yet.")


@daemon.command()
@click.option("--token", default=None, help="Daemon auth token.")
@click.option("--port", default=8788, type=int, help="Daemon port.")
@click.option("--dev", is_flag=True, help="Install development daemon settings.")
def install(token: str | None, port: int, dev: bool) -> None:
    _ = (token, port, dev)
    click.echo("Daemon install is not implemented yet.")


@daemon.command()
def status() -> None:
    click.echo("Daemon status is not implemented yet.")


@daemon.command()
def restart() -> None:
    click.echo("Daemon restart is not implemented yet.")


@daemon.command()
def uninstall() -> None:
    click.echo("Daemon uninstall is not implemented yet.")

