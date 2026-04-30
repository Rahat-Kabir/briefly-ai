from __future__ import annotations

import click

from briefly_cli import __version__
from briefly_cli.commands.brief import brief
from briefly_cli.commands.cache import cache
from briefly_cli.commands.config import config
from briefly_cli.commands.daemon import daemon
from briefly_cli.commands.slides import slides
from briefly_cli.commands.transcriber import transcriber


class BrieflyGroup(click.Group):
    """Route unknown first arguments to the hidden brief command."""

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_options(ctx, formatter)
        if self.name != "briefly":
            return
        with formatter.section("Brief Options"):
            formatter.write_dl(
                [
                    ("--extract-only, --extract", "Extract content without briefing."),
                    ("--output-format, --format TEXT", "Output format: text or markdown."),
                    (
                        "--brief-type TEXT",
                        "Brief type: standard, executive, action, study, or decision.",
                    ),
                    ("--length TEXT", "Brief length preset or character count."),
                    ("--model TEXT", "Model id or configured model preset."),
                    ("--stream TEXT", "Streaming mode: auto, on, or off."),
                    ("--timestamps", "Include transcript timestamps when available."),
                    (
                        "--max-input-chars, --max-extract-characters TEXT",
                        "Maximum extracted input characters, e.g. 50k.",
                    ),
                    ("--max-tokens, --max-output-tokens TEXT", "Maximum output tokens."),
                    ("--json", "Output structured JSON."),
                    ("--skip-cache, --no-cache", "Skip cache."),
                ]
            )

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if (
            args
            and args[0] not in self.commands
            and (args[0] == "-" or not args[0].startswith("-"))
        ):
            args.insert(0, "brief")
        return super().resolve_command(ctx, args)


@click.group(
    name="briefly",
    cls=BrieflyGroup,
    context_settings={"help_option_names": ["--help", "-h"]},
    help="Create concise briefs from text, files, and URLs.",
)
@click.version_option(__version__, "--version", prog_name="briefly", message="%(prog)s %(version)s")
def app() -> None:
    pass


app.add_command(brief)
app.add_command(cache)
app.add_command(config)
app.add_command(slides)
app.add_command(daemon)
app.add_command(transcriber)


if __name__ == "__main__":
    app()
