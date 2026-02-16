"""
Auto-Deploy Stores CLI — Main entry point.

Provides commands to wrap React/Vite web apps for mobile deployment,
build iOS/Android binaries via EAS, and submit to both app stores.
"""

import click
from rich.console import Console

from cli import __version__
from cli.commands.wrap import wrap
from cli.commands.build import build
from cli.commands.submit import submit
from cli.commands.deploy import deploy
from cli.commands.credentials import credentials
from cli.commands.status import status
from cli.commands.init_project import init_project

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="autodeploy")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False),
    default="autodeploy.yaml",
    help="Path to configuration file.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str) -> None:
    """Auto-Deploy Stores — Deploy React/Vite apps to Apple App Store & Google Play Store.

    A complete pipeline that wraps web apps using Expo + React Native,
    builds mobile binaries via EAS Build, and auto-submits to both stores.

    Provided by free sources and APIs — MIDNGHTSAPPHIRE / GlowStar Labs.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config
    ctx.obj["console"] = console


# Register command groups
cli.add_command(init_project)
cli.add_command(wrap)
cli.add_command(build)
cli.add_command(submit)
cli.add_command(deploy)
cli.add_command(credentials)
cli.add_command(status)


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
