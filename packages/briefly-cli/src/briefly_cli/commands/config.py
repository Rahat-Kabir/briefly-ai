from __future__ import annotations

import json

import click

from briefly_core.config import resolve_config_path


@click.group(help="Manage Briefly config.")
def config() -> None:
    pass


@config.command("init")
@click.option("--model", required=True, help="Default model id, e.g. openai/gpt-4o-mini.")
@click.option("--force", is_flag=True, help="Overwrite an existing config file.")
def init_config(model: str, force: bool) -> None:
    model_id = model.strip()
    if "/" not in model_id:
        raise click.BadParameter("Model must be a raw model id, e.g. openai/gpt-4o-mini.")

    config_path = resolve_config_path()
    if config_path is None:
        raise click.ClickException("Could not resolve config path. Set BRIEFLY_CONFIG.")

    if config_path.exists() and not force:
        raise click.ClickException(f"Config already exists: {config_path}")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"model": model_id}, indent=2) + "\n",
        encoding="utf-8",
    )
    click.echo(f"Wrote config: {config_path}")
