"""
Deploy command — Full pipeline: wrap → build → submit in one step.

This is the primary command for deploying a React/Vite web app to both stores.
Orchestrates the entire pipeline from source to store submission.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from cli.utils.config import load_config
from cli.utils.eas import EASClient
from cli.utils.credentials import CredentialManager


@click.command("deploy")
@click.option(
    "--target",
    "-t",
    type=click.Choice(["ios", "android", "both"]),
    default="both",
    help="Target store(s) for deployment.",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["webview", "hybrid", "native"]),
    default="webview",
    help="App wrapping mode.",
)
@click.option(
    "--track",
    type=click.Choice(["internal", "alpha", "beta", "production"]),
    default="internal",
    help="Google Play release track.",
)
@click.option("--release-notes", "-r", help="Release notes for this deployment.")
@click.option("--skip-wrap", is_flag=True, help="Skip wrapping (use existing Expo project).")
@click.option("--skip-build", is_flag=True, help="Skip building (use existing builds).")
@click.option("--dry-run", is_flag=True, help="Simulate deployment without actually submitting.")
@click.option("--parallel/--sequential", default=True, help="Build platforms in parallel.")
@click.pass_context
def deploy(
    ctx: click.Context,
    target: str,
    mode: str,
    track: str,
    release_notes: str | None,
    skip_wrap: bool,
    skip_build: bool,
    dry_run: bool,
    parallel: bool,
) -> None:
    """Deploy a React/Vite web app to Apple App Store and/or Google Play Store.

    This command runs the full pipeline: wrap → build → submit.
    Use --skip-wrap or --skip-build to skip individual steps.
    """
    console: Console = ctx.obj.get("console", Console())
    config = load_config(ctx.obj.get("config", "autodeploy.yaml"))
    verbose = ctx.obj.get("verbose", False)

    platforms = ["ios", "android"] if target == "both" else [target]
    app_name = config.get("app_name", "Unknown App")

    console.print(Panel(
        f"[bold blue]Deploying {app_name}[/bold blue]\n"
        f"Targets: {', '.join(p.upper() for p in platforms)}\n"
        f"Mode: {mode} | Track: {track}\n"
        f"{'[yellow]DRY RUN[/yellow]' if dry_run else ''}",
        title="Auto-Deploy Pipeline",
    ))

    deployment_id = f"deploy-{int(time.time())}"
    results: dict[str, Any] = {
        "deployment_id": deployment_id,
        "app_name": app_name,
        "platforms": {},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    output_path = Path(config["output_path"])
    eas = EASClient(project_dir=output_path, verbose=verbose)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        # Phase 1: Wrap
        if not skip_wrap:
            wrap_task = progress.add_task("[bold]Phase 1: Wrapping web app...[/bold]", total=100)
            try:
                ctx.invoke(
                    _get_wrap_command(),
                    mode=mode,
                    force=True,
                    skip_assets=False,
                    deep_linking=True,
                    push_notifications=True,
                    offline_support=True,
                )
                progress.update(wrap_task, completed=100,
                                description="[green]✓ Phase 1: Web app wrapped[/green]")
                results["wrap"] = {"status": "success"}
            except Exception as e:
                progress.update(wrap_task, description=f"[red]✗ Phase 1: Wrap failed: {e}[/red]")
                results["wrap"] = {"status": "failed", "error": str(e)}
                if not skip_build:
                    console.print("[red]Cannot continue without wrapping. Aborting.[/red]")
                    _save_deployment_results(results)
                    raise click.Abort()
        else:
            console.print("[dim]Skipping wrap phase (--skip-wrap)[/dim]")

        # Phase 2: Build
        build_ids: dict[str, str] = {}
        if not skip_build:
            build_task = progress.add_task("[bold]Phase 2: Building binaries...[/bold]", total=100)

            if dry_run:
                progress.update(build_task, completed=100,
                                description="[yellow]⚠ Phase 2: Build skipped (dry run)[/yellow]")
                build_ids = {p: f"dry-run-{p}" for p in platforms}
            else:
                try:
                    for plat in platforms:
                        bid = eas.build_cloud(platform=plat, profile="production")
                        build_ids[plat] = bid

                    # Wait for builds
                    completed_builds = eas.wait_for_builds(build_ids)
                    for plat, build_result in completed_builds.items():
                        results["platforms"][plat] = {
                            "build_id": build_ids[plat],
                            "build_status": build_result.get("status", "unknown"),
                        }

                    progress.update(build_task, completed=100,
                                    description="[green]✓ Phase 2: Binaries built[/green]")
                except Exception as e:
                    progress.update(build_task,
                                    description=f"[red]✗ Phase 2: Build failed: {e}[/red]")
                    results["build"] = {"status": "failed", "error": str(e)}
                    _save_deployment_results(results)
                    raise click.Abort()
        else:
            console.print("[dim]Skipping build phase (--skip-build)[/dim]")
            # Load build IDs from state
            state_file = Path(".autodeploy/state.json")
            if state_file.exists():
                state = json.loads(state_file.read_text())
                build_ids = state.get("last_build", {}).get("build_ids", {})

        # Phase 3: Submit
        submit_task = progress.add_task("[bold]Phase 3: Submitting to stores...[/bold]", total=100)

        if dry_run:
            progress.update(submit_task, completed=100,
                            description="[yellow]⚠ Phase 3: Submit skipped (dry run)[/yellow]")
        else:
            try:
                for plat in platforms:
                    if plat in build_ids:
                        submit_config: dict[str, Any] = {}
                        if plat == "android":
                            submit_config["track"] = track
                        if release_notes:
                            submit_config["releaseNotes"] = release_notes

                        submission_id = eas.submit(
                            platform=plat,
                            build_id=build_ids[plat],
                            config=submit_config,
                        )
                        if plat not in results["platforms"]:
                            results["platforms"][plat] = {}
                        results["platforms"][plat]["submission_id"] = submission_id
                        results["platforms"][plat]["submission_status"] = "submitted"

                progress.update(submit_task, completed=100,
                                description="[green]✓ Phase 3: Submitted to stores[/green]")
            except Exception as e:
                progress.update(submit_task,
                                description=f"[red]✗ Phase 3: Submit failed: {e}[/red]")
                results["submit"] = {"status": "failed", "error": str(e)}

    # Final summary
    results["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _save_deployment_results(results)
    _display_deployment_summary(console, results, dry_run)


def _get_wrap_command() -> Any:
    """Get the wrap command function."""
    from cli.commands.wrap import wrap
    return wrap


def _save_deployment_results(results: dict[str, Any]) -> None:
    """Save deployment results to state file."""
    state_file = Path(".autodeploy/state.json")
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        state = {"deployments": []}

    if "deployments" not in state:
        state["deployments"] = []

    state["deployments"].append(results)
    state["last_deployment"] = results

    state_file.parent.mkdir(exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


def _display_deployment_summary(
    console: Console,
    results: dict[str, Any],
    dry_run: bool,
) -> None:
    """Display deployment summary."""
    console.print()

    if dry_run:
        console.print(Panel(
            "[yellow]DRY RUN COMPLETE[/yellow]\n"
            "No actual builds or submissions were made.\n"
            "Remove --dry-run to deploy for real.",
            title="Deployment Summary",
        ))
        return

    summary_lines = [f"Deployment ID: {results.get('deployment_id', 'N/A')}"]

    for plat, info in results.get("platforms", {}).items():
        build_status = info.get("build_status", "N/A")
        submit_status = info.get("submission_status", "N/A")
        summary_lines.append(
            f"{plat.upper()}: Build={build_status}, Submit={submit_status}"
        )

    summary_lines.append(f"\nStarted:   {results.get('started_at', 'N/A')}")
    summary_lines.append(f"Completed: {results.get('completed_at', 'N/A')}")

    console.print(Panel(
        "\n".join(summary_lines),
        title="[bold green]Deployment Complete[/bold green]",
    ))

    console.print("\nCheck status: [bold]autodeploy status[/bold]")
    console.print("Provided by free sources and APIs — MIDNGHTSAPPHIRE / GlowStar Labs")
