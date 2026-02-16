"""
Submit command — Auto-submits built binaries to Apple App Store Connect and Google Play Console.

Handles:
- Submitting .ipa to App Store Connect via EAS Submit
- Submitting .aab to Google Play Console via EAS Submit
- Configuring submission metadata (release notes, track, etc.)
- Monitoring submission status
"""

import json
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from cli.utils.config import load_config
from cli.utils.eas import EASClient
from cli.utils.credentials import CredentialManager


@click.command("submit")
@click.option(
    "--platform",
    "-p",
    type=click.Choice(["ios", "android", "all"]),
    default="all",
    help="Target store to submit to.",
)
@click.option("--build-id", help="Specific build ID to submit. Uses latest if not specified.")
@click.option(
    "--track",
    type=click.Choice(["internal", "alpha", "beta", "production"]),
    default="internal",
    help="Google Play release track.",
)
@click.option(
    "--release-notes",
    "-r",
    help="Release notes for this submission.",
)
@click.option("--auto-release/--no-auto-release", default=False,
              help="Automatically release after review (iOS) or approval (Android).")
@click.pass_context
def submit(
    ctx: click.Context,
    platform: str,
    build_id: str | None,
    track: str,
    release_notes: str | None,
    auto_release: bool,
) -> None:
    """Submit built binaries to Apple App Store and/or Google Play Store."""
    console: Console = ctx.obj.get("console", Console())
    config = load_config(ctx.obj.get("config", "autodeploy.yaml"))
    verbose = ctx.obj.get("verbose", False)

    output_path = Path(config["output_path"])
    eas = EASClient(project_dir=output_path, verbose=verbose)
    cred_manager = CredentialManager()

    platforms = ["ios", "android"] if platform == "all" else [platform]

    # Resolve build IDs
    build_ids = _resolve_build_ids(console, eas, build_id, platforms)

    if not build_ids:
        console.print("[red]Error:[/red] No builds found to submit. Run [bold]autodeploy build[/bold] first.")
        raise click.Abort()

    # Submit to each platform
    submission_ids: dict[str, str] = {}

    for plat in platforms:
        if plat not in build_ids:
            console.print(f"[yellow]⚠[/yellow] No {plat.upper()} build found, skipping.")
            continue

        console.print(f"\n[bold blue]Submitting to {_store_name(plat)}...[/bold blue]")

        submit_config: dict[str, Any] = {}

        if plat == "ios":
            submit_config = _prepare_ios_submission(
                console, cred_manager, config, release_notes, auto_release
            )
        elif plat == "android":
            submit_config = _prepare_android_submission(
                console, cred_manager, config, track, release_notes, auto_release
            )

        submission_id = eas.submit(
            platform=plat,
            build_id=build_ids[plat],
            config=submit_config,
        )
        submission_ids[plat] = submission_id
        console.print(f"  Submission ID: [bold]{submission_id}[/bold]")

    # Monitor submissions
    if submission_ids:
        console.print("\n[bold]Monitoring submission status...[/bold]")
        _monitor_submissions(console, eas, submission_ids)

    # Save submission state
    _save_submission_state(submission_ids, build_ids, track)

    console.print("\n[bold green]Submission process complete![/bold green]")


def _store_name(platform: str) -> str:
    """Get the human-readable store name."""
    return "Apple App Store" if platform == "ios" else "Google Play Store"


def _resolve_build_ids(
    console: Console,
    eas: EASClient,
    explicit_build_id: str | None,
    platforms: list[str],
) -> dict[str, str]:
    """Resolve build IDs for submission."""
    build_ids: dict[str, str] = {}

    if explicit_build_id:
        # Use the same build ID for all platforms (user specified)
        for plat in platforms:
            build_ids[plat] = explicit_build_id
    else:
        # Try to get from saved state
        state_file = Path(".autodeploy/state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            last_build = state.get("last_build", {})
            saved_ids = last_build.get("build_ids", {})
            for plat in platforms:
                if plat in saved_ids:
                    build_ids[plat] = saved_ids[plat]

        # Fall back to latest EAS builds
        if not build_ids:
            for plat in platforms:
                latest = eas.get_latest_build(platform=plat, profile="production")
                if latest:
                    build_ids[plat] = latest["id"]

    return build_ids


def _prepare_ios_submission(
    console: Console,
    cred_manager: CredentialManager,
    config: dict[str, Any],
    release_notes: str | None,
    auto_release: bool,
) -> dict[str, Any]:
    """Prepare iOS submission configuration."""
    submit_config: dict[str, Any] = {
        "ascAppId": config.get("apple_app_id", ""),
        "appleTeamId": config.get("apple_team_id", ""),
    }

    # Apple API key
    apple_key = cred_manager.get_credential("apple_api_key")
    if apple_key:
        submit_config["ascApiKeyId"] = apple_key.get("key_id", "")
        submit_config["ascApiKeyIssuerId"] = apple_key.get("issuer_id", "")
        submit_config["ascApiKeyPath"] = apple_key.get("key_path", "")
        console.print("  [green]✓[/green] Apple API key configured")

    if release_notes:
        submit_config["releaseNotes"] = release_notes

    if auto_release:
        submit_config["autoRelease"] = True

    return submit_config


def _prepare_android_submission(
    console: Console,
    cred_manager: CredentialManager,
    config: dict[str, Any],
    track: str,
    release_notes: str | None,
    auto_release: bool,
) -> dict[str, Any]:
    """Prepare Android submission configuration."""
    submit_config: dict[str, Any] = {
        "track": track,
        "releaseStatus": "completed" if auto_release else "draft",
    }

    # Google service account
    google_key = cred_manager.get_credential("google_service_account")
    if google_key:
        key_path = google_key.get("key_path", "")
        submit_config["serviceAccountKeyPath"] = key_path
        console.print("  [green]✓[/green] Google Play service account configured")
    else:
        key_path = config.get("google_service_account_key", "")
        if key_path and Path(key_path).exists():
            submit_config["serviceAccountKeyPath"] = key_path
            console.print("  [green]✓[/green] Google Play service account key file found")

    if release_notes:
        submit_config["releaseNotes"] = {"en-US": release_notes}

    return submit_config


def _monitor_submissions(
    console: Console,
    eas: EASClient,
    submission_ids: dict[str, str],
) -> None:
    """Monitor submission progress."""
    pending = set(submission_ids.keys())
    max_wait = 300  # 5 minutes max wait
    elapsed = 0

    while pending and elapsed < max_wait:
        for plat in list(pending):
            status = eas.get_submission_status(submission_ids[plat])
            state = status.get("status", "unknown")

            if state in ("finished", "errored"):
                pending.discard(plat)
                icon = "[green]✓[/green]" if state == "finished" else "[red]✗[/red]"
                console.print(f"  {icon} {_store_name(plat)}: {state}")

        if pending:
            time.sleep(10)
            elapsed += 10

    if pending:
        console.print("[yellow]⚠ Some submissions still in progress. Check status with:[/yellow]")
        console.print("  [bold]autodeploy status[/bold]")


def _save_submission_state(
    submission_ids: dict[str, str],
    build_ids: dict[str, str],
    track: str,
) -> None:
    """Save submission state."""
    state_file = Path(".autodeploy/state.json")
    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        state = {}

    state["last_submit"] = {
        "submission_ids": submission_ids,
        "build_ids": build_ids,
        "track": track,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    state_file.parent.mkdir(exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))
