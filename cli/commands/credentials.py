"""
Credentials command — Manage store credentials securely.

Handles:
- Apple Developer account credentials (App Store Connect API key)
- Google Play Console service account JSON
- iOS signing certificates and provisioning profiles
- Android keystore files
- All stored encrypted using the glowstarlabs-vault pattern
"""

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cli.utils.credentials import CredentialManager


@click.group("credentials")
@click.pass_context
def credentials(ctx: click.Context) -> None:
    """Manage store credentials (Apple, Google, signing keys)."""
    pass


@credentials.command("setup")
@click.option("--interactive/--non-interactive", default=True,
              help="Run in interactive mode with prompts.")
@click.pass_context
def setup(ctx: click.Context, interactive: bool) -> None:
    """Set up all required credentials interactively."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    console.print(Panel("[bold blue]Credential Setup Wizard[/bold blue]"))

    if interactive:
        # Apple credentials
        console.print("\n[bold]1. Apple App Store Connect[/bold]")
        setup_apple = click.confirm("Configure Apple credentials?", default=True)
        if setup_apple:
            _setup_apple_credentials(console, cred_manager)

        # Google credentials
        console.print("\n[bold]2. Google Play Console[/bold]")
        setup_google = click.confirm("Configure Google Play credentials?", default=True)
        if setup_google:
            _setup_google_credentials(console, cred_manager)

        # Android keystore
        console.print("\n[bold]3. Android Keystore[/bold]")
        setup_keystore = click.confirm("Configure Android keystore?", default=True)
        if setup_keystore:
            _setup_android_keystore(console, cred_manager)

    console.print("\n[bold green]Credential setup complete![/bold green]")


@credentials.command("list")
@click.pass_context
def list_credentials(ctx: click.Context) -> None:
    """List all stored credentials."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    creds = cred_manager.list_credentials()

    if not creds:
        console.print("[yellow]No credentials stored yet.[/yellow]")
        console.print("Run [bold]autodeploy credentials setup[/bold] to configure.")
        return

    table = Table(title="Stored Credentials")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Last Updated")

    for cred in creds:
        status = "[green]✓ Valid[/green]" if cred.get("valid") else "[yellow]⚠ Unverified[/yellow]"
        table.add_row(
            cred["name"],
            cred["type"],
            status,
            cred.get("updated_at", "N/A"),
        )

    console.print(table)


@credentials.command("add")
@click.argument("name")
@click.argument("credential_type", type=click.Choice([
    "apple_api_key", "google_service_account", "android_keystore",
    "ios_certificate", "ios_provisioning_profile", "custom",
]))
@click.option("--file", "-f", "file_path", type=click.Path(exists=True),
              help="Path to credential file.")
@click.option("--value", "-v", help="Credential value (for simple key/value credentials).")
@click.option("--metadata", "-m", help="JSON metadata for the credential.")
@click.pass_context
def add(
    ctx: click.Context,
    name: str,
    credential_type: str,
    file_path: str | None,
    value: str | None,
    metadata: str | None,
) -> None:
    """Add a new credential to the vault."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    meta = json.loads(metadata) if metadata else {}

    if file_path:
        cred_manager.store_credential_file(
            name=name,
            credential_type=credential_type,
            file_path=file_path,
            metadata=meta,
        )
    elif value:
        cred_manager.store_credential(
            name=name,
            credential_type=credential_type,
            value=value,
            metadata=meta,
        )
    else:
        console.print("[red]Error:[/red] Provide either --file or --value.")
        raise click.Abort()

    console.print(f"[green]✓[/green] Credential [bold]{name}[/bold] stored successfully.")


@credentials.command("remove")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
def remove(ctx: click.Context, name: str, force: bool) -> None:
    """Remove a credential from the vault."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    if not force:
        if not click.confirm(f"Remove credential '{name}'?"):
            return

    cred_manager.remove_credential(name)
    console.print(f"[green]✓[/green] Credential [bold]{name}[/bold] removed.")


@credentials.command("verify")
@click.option("--platform", "-p", type=click.Choice(["ios", "android", "all"]), default="all")
@click.pass_context
def verify(ctx: click.Context, platform: str) -> None:
    """Verify stored credentials are valid and usable."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    platforms = ["ios", "android"] if platform == "all" else [platform]

    for plat in platforms:
        console.print(f"\n[bold]Verifying {plat.upper()} credentials...[/bold]")

        if plat == "ios":
            results = cred_manager.verify_apple_credentials()
        else:
            results = cred_manager.verify_google_credentials()

        for check, passed in results.items():
            icon = "[green]✓[/green]" if passed else "[red]✗[/red]"
            console.print(f"  {icon} {check}")


@credentials.command("rotate")
@click.argument("name")
@click.pass_context
def rotate(ctx: click.Context, name: str) -> None:
    """Rotate a credential (generate new, archive old)."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    console.print(f"[bold]Rotating credential: {name}[/bold]")
    cred_manager.rotate_credential(name)
    console.print(f"[green]✓[/green] Credential [bold]{name}[/bold] rotated successfully.")


@credentials.command("export")
@click.option("--format", "-f", "fmt", type=click.Choice(["env", "json", "yaml"]), default="env")
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.pass_context
def export_credentials(ctx: click.Context, fmt: str, output: str | None) -> None:
    """Export credentials in various formats (for CI/CD)."""
    console: Console = ctx.obj.get("console", Console())
    cred_manager = CredentialManager()

    exported = cred_manager.export_credentials(format=fmt)

    if output:
        Path(output).write_text(exported)
        console.print(f"[green]✓[/green] Credentials exported to [bold]{output}[/bold]")
    else:
        console.print(exported)


def _setup_apple_credentials(console: Console, cred_manager: CredentialManager) -> None:
    """Interactive Apple credential setup."""
    console.print("  You need an App Store Connect API key.")
    console.print("  Generate one at: https://appstoreconnect.apple.com/access/api")
    console.print()

    key_id = click.prompt("  API Key ID")
    issuer_id = click.prompt("  Issuer ID")
    key_path = click.prompt("  Path to .p8 key file", type=click.Path(exists=True))

    cred_manager.store_credential(
        name="apple_api_key",
        credential_type="apple_api_key",
        value=json.dumps({
            "key_id": key_id,
            "issuer_id": issuer_id,
            "key_path": str(Path(key_path).resolve()),
        }),
        metadata={"key_id": key_id, "issuer_id": issuer_id},
    )

    # Apple Team ID
    team_id = click.prompt("  Apple Team ID")
    cred_manager.store_credential(
        name="apple_team_id",
        credential_type="custom",
        value=team_id,
    )

    console.print("  [green]✓[/green] Apple credentials stored")


def _setup_google_credentials(console: Console, cred_manager: CredentialManager) -> None:
    """Interactive Google Play credential setup."""
    console.print("  You need a Google Play Console service account JSON key.")
    console.print("  Create one at: https://console.cloud.google.com/iam-admin/serviceaccounts")
    console.print()

    key_path = click.prompt(
        "  Path to service account JSON file",
        type=click.Path(exists=True),
    )

    cred_manager.store_credential_file(
        name="google_service_account",
        credential_type="google_service_account",
        file_path=key_path,
    )

    console.print("  [green]✓[/green] Google Play credentials stored")


def _setup_android_keystore(console: Console, cred_manager: CredentialManager) -> None:
    """Interactive Android keystore setup."""
    console.print("  You can use an existing keystore or let EAS generate one.")
    console.print()

    use_existing = click.confirm("  Use an existing keystore?", default=False)

    if use_existing:
        keystore_path = click.prompt(
            "  Path to keystore file (.jks or .keystore)",
            type=click.Path(exists=True),
        )
        keystore_password = click.prompt("  Keystore password", hide_input=True)
        key_alias = click.prompt("  Key alias")
        key_password = click.prompt("  Key password", hide_input=True)

        cred_manager.store_credential(
            name="android_keystore",
            credential_type="android_keystore",
            value=json.dumps({
                "keystore_path": str(Path(keystore_path).resolve()),
                "keystore_password": keystore_password,
                "key_alias": key_alias,
                "key_password": key_password,
            }),
        )
        console.print("  [green]✓[/green] Android keystore stored")
    else:
        console.print("  [dim]EAS will generate a keystore during the first build.[/dim]")
