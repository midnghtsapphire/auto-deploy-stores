"""
Initialize a new auto-deploy project configuration.

Creates the autodeploy.yaml config and sets up the project structure
for wrapping a React/Vite web app into an Expo mobile app.
"""

import os
import json
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.panel import Panel

from cli.utils.config import AutoDeployConfig, generate_default_config


@click.command("init")
@click.option("--name", "-n", prompt="App name", help="Display name of the app.")
@click.option(
    "--bundle-id",
    "-b",
    prompt="Bundle identifier (e.g., com.company.app)",
    help="Unique bundle identifier.",
)
@click.option(
    "--source",
    "-s",
    type=click.Path(exists=True),
    prompt="Path to React/Vite web app source",
    help="Path to the existing web app to wrap.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./mobile",
    help="Output directory for the Expo project.",
)
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["ios", "android", "both"]),
    default="both",
    help="Target platform(s).",
)
@click.pass_context
def init_project(
    ctx: click.Context,
    name: str,
    bundle_id: str,
    source: str,
    output: str,
    platform: str,
) -> None:
    """Initialize a new auto-deploy project with configuration."""
    console: Console = ctx.obj.get("console", Console())
    config_path = ctx.obj.get("config", "autodeploy.yaml")

    console.print(Panel(f"[bold blue]Initializing Auto-Deploy Project: {name}[/bold blue]"))

    config = generate_default_config(
        app_name=name,
        bundle_id=bundle_id,
        source_path=str(Path(source).resolve()),
        output_path=str(Path(output).resolve()),
        platform=platform,
    )

    # Write config file
    config_file = Path(config_path)
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]✓[/green] Configuration written to [bold]{config_file}[/bold]")

    # Create output directory structure
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]✓[/green] Output directory created at [bold]{output_dir}[/bold]")

    # Create .autodeploy directory for local state
    state_dir = Path(".autodeploy")
    state_dir.mkdir(exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "initialized": True,
                "app_name": name,
                "bundle_id": bundle_id,
                "last_build": None,
                "last_submit": None,
                "deployments": [],
            },
            indent=2,
        )
    )

    console.print(f"[green]✓[/green] State directory created at [bold]{state_dir}[/bold]")
    console.print()
    console.print("[bold green]Project initialized successfully![/bold green]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Configure credentials: [bold]autodeploy credentials setup[/bold]")
    console.print("  2. Wrap your web app:     [bold]autodeploy wrap[/bold]")
    console.print("  3. Build binaries:        [bold]autodeploy build[/bold]")
    console.print("  4. Deploy to stores:      [bold]autodeploy deploy --target both[/bold]")
