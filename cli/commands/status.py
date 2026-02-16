"""
Status command — Monitor deployment, build, and submission status.
"""

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.utils.config import load_config
from cli.utils.eas import EASClient


@click.command("status")
@click.option("--deployment-id", "-d", help="Specific deployment ID to check.")
@click.option("--build-id", "-b", help="Specific build ID to check.")
@click.option("--all", "show_all", is_flag=True, help="Show all deployments.")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON.")
@click.pass_context
def status(
    ctx: click.Context,
    deployment_id: str | None,
    build_id: str | None,
    show_all: bool,
    json_out: bool,
) -> None:
    """Check deployment, build, and submission status."""
    console: Console = ctx.obj.get("console", Console())

    state_file = Path(".autodeploy/state.json")
    if not state_file.exists():
        console.print("[yellow]No deployment state found.[/yellow]")
        console.print("Run [bold]autodeploy deploy[/bold] to start a deployment.")
        return

    state = json.loads(state_file.read_text())

    if json_out:
        console.print_json(json.dumps(state, indent=2))
        return

    # Show last deployment
    if not show_all and not deployment_id and not build_id:
        last = state.get("last_deployment")
        if last:
            _display_deployment(console, last)
        else:
            console.print("[yellow]No deployments found.[/yellow]")
        return

    # Show all deployments
    if show_all:
        deployments = state.get("deployments", [])
        if not deployments:
            console.print("[yellow]No deployments found.[/yellow]")
            return

        table = Table(title="All Deployments")
        table.add_column("ID", style="bold")
        table.add_column("App")
        table.add_column("Platforms")
        table.add_column("Started")
        table.add_column("Status")

        for dep in reversed(deployments):
            platforms = ", ".join(dep.get("platforms", {}).keys())
            dep_status = _get_overall_status(dep)
            table.add_row(
                dep.get("deployment_id", "N/A"),
                dep.get("app_name", "N/A"),
                platforms.upper(),
                dep.get("started_at", "N/A"),
                dep_status,
            )

        console.print(table)

    # Check specific build
    if build_id:
        try:
            config = load_config(ctx.obj.get("config", "autodeploy.yaml"))
            output_path = Path(config["output_path"])
            eas = EASClient(project_dir=output_path)
            build_status = eas.get_build_status(build_id)
            console.print(Panel(
                json.dumps(build_status, indent=2),
                title=f"Build {build_id}",
            ))
        except Exception as e:
            console.print(f"[red]Error checking build status:[/red] {e}")


def _display_deployment(console: Console, deployment: dict[str, Any]) -> None:
    """Display a single deployment's details."""
    lines = [
        f"[bold]Deployment ID:[/bold] {deployment.get('deployment_id', 'N/A')}",
        f"[bold]App:[/bold] {deployment.get('app_name', 'N/A')}",
        f"[bold]Started:[/bold] {deployment.get('started_at', 'N/A')}",
        f"[bold]Completed:[/bold] {deployment.get('completed_at', 'N/A')}",
        "",
    ]

    for plat, info in deployment.get("platforms", {}).items():
        build_status = info.get("build_status", "N/A")
        submit_status = info.get("submission_status", "N/A")
        build_id = info.get("build_id", "N/A")
        submission_id = info.get("submission_id", "N/A")

        lines.append(f"[bold]{plat.upper()}:[/bold]")
        lines.append(f"  Build:      {build_status} (ID: {build_id})")
        lines.append(f"  Submission: {submit_status} (ID: {submission_id})")

    console.print(Panel("\n".join(lines), title="Last Deployment"))


def _get_overall_status(deployment: dict[str, Any]) -> str:
    """Get overall deployment status."""
    platforms = deployment.get("platforms", {})
    if not platforms:
        return "[yellow]Unknown[/yellow]"

    all_submitted = all(
        p.get("submission_status") == "submitted" for p in platforms.values()
    )
    any_failed = any(
        p.get("build_status") == "errored" or p.get("submission_status") == "errored"
        for p in platforms.values()
    )

    if any_failed:
        return "[red]Failed[/red]"
    elif all_submitted:
        return "[green]Submitted[/green]"
    else:
        return "[blue]In Progress[/blue]"
