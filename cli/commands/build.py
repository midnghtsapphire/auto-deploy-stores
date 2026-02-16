"""
Build command — Builds iOS (.ipa) and Android (.apk/.aab) binaries via EAS Build.

Handles:
- Triggering EAS Build for iOS and/or Android
- Managing build profiles (development, preview, production)
- Monitoring build progress
- Downloading build artifacts
- Managing signing certificates and keystores
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli.utils.config import load_config
from cli.utils.eas import EASClient
from cli.utils.credentials import CredentialManager


@click.command("build")
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["ios", "android", "all"]),
    default="all",
    help="Target platform to build.",
)
@click.option(
    "--profile",
    type=click.Choice(["development", "preview", "production"]),
    default="production",
    help="Build profile to use.",
)
@click.option("--local", is_flag=True, help="Build locally instead of using EAS cloud.")
@click.option("--wait/--no-wait", default=True, help="Wait for build to complete.")
@click.option("--download/--no-download", default=True, help="Download artifacts after build.")
@click.option("--auto-submit", is_flag=True, help="Auto-submit to stores after successful build.")
@click.pass_context
def build(
    ctx: click.Context,
    platform: str,
    profile: str,
    local: bool,
    wait: bool,
    download: bool,
    auto_submit: bool,
) -> None:
    """Build iOS and Android binaries using EAS Build."""
    console: Console = ctx.obj.get("console", Console())
    config = load_config(ctx.obj.get("config", "autodeploy.yaml"))
    verbose = ctx.obj.get("verbose", False)

    output_path = Path(config["output_path"])
    if not output_path.exists():
        console.print("[red]Error:[/red] Expo project not found. Run [bold]autodeploy wrap[/bold] first.")
        raise click.Abort()

    eas = EASClient(project_dir=output_path, verbose=verbose)
    cred_manager = CredentialManager()

    # Validate credentials
    console.print("[bold]Validating build credentials...[/bold]")
    _validate_credentials(console, cred_manager, platform, config)

    # Configure signing
    console.print("[bold]Configuring code signing...[/bold]")
    _configure_signing(console, eas, cred_manager, platform, config)

    # Trigger builds
    build_ids: dict[str, str] = {}

    platforms = ["ios", "android"] if platform == "all" else [platform]

    for plat in platforms:
        console.print(f"\n[bold blue]Starting {plat.upper()} build ({profile} profile)...[/bold blue]")

        if local:
            build_id = eas.build_local(platform=plat, profile=profile)
        else:
            build_id = eas.build_cloud(platform=plat, profile=profile)

        build_ids[plat] = build_id
        console.print(f"  Build ID: [bold]{build_id}[/bold]")

    # Wait for builds
    if wait and not local:
        console.print("\n[bold]Waiting for builds to complete...[/bold]")
        results = _wait_for_builds(console, eas, build_ids)

        # Display results
        _display_build_results(console, results)

        # Download artifacts
        if download:
            console.print("\n[bold]Downloading build artifacts...[/bold]")
            artifacts_dir = output_path / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)

            for plat, result in results.items():
                if result.get("status") == "finished":
                    artifact_path = eas.download_artifact(
                        build_id=result["id"],
                        output_dir=artifacts_dir,
                    )
                    console.print(
                        f"  [green]✓[/green] {plat.upper()}: {artifact_path}"
                    )

        # Auto-submit
        if auto_submit:
            console.print("\n[bold]Auto-submitting to stores...[/bold]")
            for plat, result in results.items():
                if result.get("status") == "finished":
                    eas.submit(platform=plat, build_id=result["id"])
                    console.print(f"  [green]✓[/green] {plat.upper()} submission started")

    # Save build state
    _save_build_state(config, build_ids, profile)

    console.print("\n[bold green]Build process complete![/bold green]")


def _validate_credentials(
    console: Console,
    cred_manager: CredentialManager,
    platform: str,
    config: dict[str, Any],
) -> None:
    """Validate that required credentials are available."""
    platforms = ["ios", "android"] if platform == "all" else [platform]

    for plat in platforms:
        if plat == "ios":
            has_apple = cred_manager.has_credential("apple_api_key")
            if has_apple:
                console.print("  [green]✓[/green] Apple App Store Connect API key found")
            else:
                console.print(
                    "  [yellow]⚠[/yellow] Apple API key not found — EAS will use interactive auth"
                )

        elif plat == "android":
            has_google = cred_manager.has_credential("google_service_account")
            if has_google:
                console.print("  [green]✓[/green] Google Play service account found")
            else:
                keypath = config.get("google_service_account_key", "")
                if keypath and Path(keypath).exists():
                    console.print("  [green]✓[/green] Google Play service account key file found")
                else:
                    console.print(
                        "  [yellow]⚠[/yellow] Google service account not found — "
                        "submission will require manual setup"
                    )


def _configure_signing(
    console: Console,
    eas: EASClient,
    cred_manager: CredentialManager,
    platform: str,
    config: dict[str, Any],
) -> None:
    """Configure code signing for the target platforms."""
    platforms = ["ios", "android"] if platform == "all" else [platform]

    for plat in platforms:
        if plat == "ios":
            # iOS signing is managed by EAS credentials service
            console.print("  [dim]iOS signing managed by EAS credentials service[/dim]")

            # Set Apple API key if available
            apple_key = cred_manager.get_credential("apple_api_key")
            if apple_key:
                eas.set_apple_credentials(
                    key_id=apple_key.get("key_id", ""),
                    issuer_id=apple_key.get("issuer_id", ""),
                    key_path=apple_key.get("key_path", ""),
                )
                console.print("  [green]✓[/green] Apple API key configured for EAS")

        elif plat == "android":
            # Android keystore
            keystore_path = config.get("android_keystore_path")
            if keystore_path and Path(keystore_path).exists():
                console.print(f"  [green]✓[/green] Android keystore found: {keystore_path}")
            else:
                console.print("  [dim]Android keystore managed by EAS credentials service[/dim]")


def _wait_for_builds(
    console: Console,
    eas: EASClient,
    build_ids: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Wait for all builds to complete and return results."""
    results: dict[str, dict[str, Any]] = {}
    pending = set(build_ids.keys())

    with Live(console=console, refresh_per_second=1) as live:
        while pending:
            table = Table(title="Build Status")
            table.add_column("Platform", style="bold")
            table.add_column("Build ID")
            table.add_column("Status")
            table.add_column("Duration")

            for plat, build_id in build_ids.items():
                status_info = eas.get_build_status(build_id)
                status = status_info.get("status", "unknown")

                if status in ("finished", "errored", "canceled"):
                    pending.discard(plat)
                    results[plat] = status_info

                status_style = {
                    "finished": "[green]finished[/green]",
                    "errored": "[red]errored[/red]",
                    "canceled": "[yellow]canceled[/yellow]",
                    "in-queue": "[dim]in-queue[/dim]",
                    "in-progress": "[blue]in-progress[/blue]",
                }.get(status, status)

                table.add_row(
                    plat.upper(),
                    build_id[:12] + "...",
                    status_style,
                    status_info.get("duration", "—"),
                )

            live.update(table)

            if pending:
                time.sleep(10)

    return results


def _display_build_results(
    console: Console,
    results: dict[str, dict[str, Any]],
) -> None:
    """Display build results summary."""
    table = Table(title="Build Results")
    table.add_column("Platform", style="bold")
    table.add_column("Status")
    table.add_column("Artifact")
    table.add_column("Size")

    for plat, result in results.items():
        status = result.get("status", "unknown")
        artifact = result.get("artifact_url", "—")
        size = result.get("artifact_size", "—")

        status_display = (
            "[green]✓ Success[/green]" if status == "finished" else f"[red]✗ {status}[/red]"
        )

        table.add_row(plat.upper(), status_display, artifact[:50] + "..." if len(str(artifact)) > 50 else str(artifact), str(size))

    console.print(table)


def _save_build_state(
    config: dict[str, Any],
    build_ids: dict[str, str],
    profile: str,
) -> None:
    """Save build state for later reference."""
    state_file = Path(".autodeploy/state.json")
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        state = {}

    state["last_build"] = {
        "build_ids": build_ids,
        "profile": profile,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    state_file.parent.mkdir(exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))
