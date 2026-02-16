"""
Wrap command — Takes a React/Vite web app and wraps it into an Expo/React Native project.

Handles:
- Copying web app assets into the Expo project
- Generating app.json / app.config.js with proper configuration
- Setting up WebView wrapper or React Native Web conversion
- Generating app icons and splash screens from existing assets
- Configuring deep linking, push notifications, and offline support
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli.utils.config import load_config
from cli.utils.assets import generate_app_icons, generate_splash_screens
from cli.utils.template_engine import TemplateEngine


@click.command("wrap")
@click.option("--mode", "-m", type=click.Choice(["webview", "hybrid", "native"]), default="webview",
              help="Wrapping mode: webview (WebView wrapper), hybrid (partial native), native (full conversion).")
@click.option("--force", "-f", is_flag=True, help="Force overwrite existing Expo project.")
@click.option("--skip-assets", is_flag=True, help="Skip icon/splash screen generation.")
@click.option("--deep-linking/--no-deep-linking", default=True, help="Enable deep linking support.")
@click.option("--push-notifications/--no-push-notifications", default=True,
              help="Enable push notification support.")
@click.option("--offline-support/--no-offline-support", default=True, help="Enable offline support.")
@click.pass_context
def wrap(
    ctx: click.Context,
    mode: str,
    force: bool,
    skip_assets: bool,
    deep_linking: bool,
    push_notifications: bool,
    offline_support: bool,
) -> None:
    """Wrap a React/Vite web app into an Expo/React Native project."""
    console: Console = ctx.obj.get("console", Console())
    config = load_config(ctx.obj.get("config", "autodeploy.yaml"))

    source_path = Path(config["source_path"])
    output_path = Path(config["output_path"])
    app_name = config["app_name"]
    bundle_id = config["bundle_id"]

    if not source_path.exists():
        console.print(f"[red]Error:[/red] Source path does not exist: {source_path}")
        raise click.Abort()

    if output_path.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Output directory exists: {output_path}\n"
            "Use --force to overwrite."
        )
        raise click.Abort()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Initialize Expo project structure
        task = progress.add_task("Creating Expo project structure...", total=None)
        engine = TemplateEngine()
        engine.create_expo_project(
            output_path=output_path,
            app_name=app_name,
            bundle_id=bundle_id,
            mode=mode,
            features={
                "deep_linking": deep_linking,
                "push_notifications": push_notifications,
                "offline_support": offline_support,
            },
        )
        progress.update(task, description="[green]✓ Expo project structure created[/green]")

        # Step 2: Copy web app source
        task2 = progress.add_task("Copying web app source...", total=None)
        web_dir = output_path / "web-source"
        if web_dir.exists():
            shutil.rmtree(web_dir)
        shutil.copytree(source_path, web_dir, ignore=shutil.ignore_patterns(
            "node_modules", ".git", ".next", "dist", "build", "__pycache__"
        ))
        progress.update(task2, description="[green]✓ Web app source copied[/green]")

        # Step 3: Generate app.json
        task3 = progress.add_task("Generating app configuration...", total=None)
        app_config = generate_app_config(
            app_name=app_name,
            bundle_id=bundle_id,
            mode=mode,
            features={
                "deep_linking": deep_linking,
                "push_notifications": push_notifications,
                "offline_support": offline_support,
            },
            config=config,
        )
        with open(output_path / "app.json", "w") as f:
            json.dump(app_config, f, indent=2)
        progress.update(task3, description="[green]✓ App configuration generated[/green]")

        # Step 4: Generate EAS configuration
        task4 = progress.add_task("Generating EAS build configuration...", total=None)
        eas_config = generate_eas_config(config)
        with open(output_path / "eas.json", "w") as f:
            json.dump(eas_config, f, indent=2)
        progress.update(task4, description="[green]✓ EAS configuration generated[/green]")

        # Step 5: Generate assets (icons, splash screens)
        if not skip_assets:
            task5 = progress.add_task("Generating app icons and splash screens...", total=None)
            assets_dir = output_path / "assets"
            assets_dir.mkdir(exist_ok=True)

            source_icon = _find_source_icon(source_path)
            if source_icon:
                generate_app_icons(source_icon, assets_dir)
                generate_splash_screens(source_icon, assets_dir, app_name)
                progress.update(
                    task5,
                    description="[green]✓ App icons and splash screens generated[/green]",
                )
            else:
                progress.update(
                    task5,
                    description="[yellow]⚠ No source icon found — using defaults[/yellow]",
                )

        # Step 6: Install dependencies
        task6 = progress.add_task("Generating package.json...", total=None)
        package_json = generate_package_json(app_name, bundle_id, mode, {
            "deep_linking": deep_linking,
            "push_notifications": push_notifications,
            "offline_support": offline_support,
        })
        with open(output_path / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        progress.update(task6, description="[green]✓ package.json generated[/green]")

    console.print()
    console.print(f"[bold green]✓ App wrapped successfully![/bold green]")
    console.print(f"  Output: [bold]{output_path}[/bold]")
    console.print(f"  Mode:   [bold]{mode}[/bold]")
    console.print()
    console.print("Next: Run [bold]autodeploy build[/bold] to create mobile binaries.")


def _find_source_icon(source_path: Path) -> Path | None:
    """Find an icon file in the source web app."""
    candidates = [
        "public/favicon.svg",
        "public/favicon.png",
        "public/icon.png",
        "public/logo.png",
        "public/logo.svg",
        "src/assets/icon.png",
        "src/assets/logo.png",
        "public/apple-touch-icon.png",
        "public/android-chrome-512x512.png",
        "public/android-chrome-192x192.png",
    ]
    for candidate in candidates:
        path = source_path / candidate
        if path.exists():
            return path
    return None


def generate_app_config(
    app_name: str,
    bundle_id: str,
    mode: str,
    features: dict[str, bool],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Generate Expo app.json configuration."""
    scheme = app_name.lower().replace(" ", "").replace("-", "")
    slug = app_name.lower().replace(" ", "-")

    app_config: dict[str, Any] = {
        "expo": {
            "name": app_name,
            "slug": slug,
            "version": config.get("version", "1.0.0"),
            "orientation": "portrait",
            "icon": "./assets/icon.png",
            "userInterfaceStyle": "automatic",
            "splash": {
                "image": "./assets/splash.png",
                "resizeMode": "contain",
                "backgroundColor": config.get("splash_background", "#ffffff"),
            },
            "assetBundlePatterns": ["**/*"],
            "ios": {
                "supportsTablet": True,
                "bundleIdentifier": bundle_id,
                "buildNumber": config.get("build_number", "1"),
                "infoPlist": {},
            },
            "android": {
                "adaptiveIcon": {
                    "foregroundImage": "./assets/adaptive-icon.png",
                    "backgroundColor": config.get("icon_background", "#ffffff"),
                },
                "package": bundle_id,
                "versionCode": int(config.get("version_code", 1)),
                "permissions": [],
            },
            "web": {
                "favicon": "./assets/favicon.png",
                "bundler": "metro",
            },
            "plugins": [],
            "extra": {
                "eas": {
                    "projectId": config.get("eas_project_id", ""),
                },
                "wrapMode": mode,
            },
        }
    }

    # Deep linking
    if features.get("deep_linking"):
        app_config["expo"]["scheme"] = scheme
        app_config["expo"]["plugins"].append("expo-linking")

    # Push notifications
    if features.get("push_notifications"):
        app_config["expo"]["plugins"].append("expo-notifications")
        app_config["expo"]["ios"]["infoPlist"]["UIBackgroundModes"] = ["remote-notification"]
        app_config["expo"]["android"]["permissions"].append("RECEIVE_BOOT_COMPLETED")

    # Offline support
    if features.get("offline_support"):
        app_config["expo"]["plugins"].append("expo-updates")
        app_config["expo"]["updates"] = {
            "enabled": True,
            "fallbackToCacheTimeout": 30000,
        }

    return app_config


def generate_eas_config(config: dict[str, Any]) -> dict[str, Any]:
    """Generate EAS build and submit configuration."""
    return {
        "cli": {
            "version": ">= 12.0.0",
            "appVersionSource": "remote",
        },
        "build": {
            "development": {
                "developmentClient": True,
                "distribution": "internal",
                "ios": {
                    "simulator": True,
                },
            },
            "preview": {
                "distribution": "internal",
                "ios": {
                    "simulator": False,
                },
                "android": {
                    "buildType": "apk",
                },
            },
            "production": {
                "ios": {
                    "autoIncrement": True,
                    "credentialsSource": "remote",
                },
                "android": {
                    "autoIncrement": True,
                    "credentialsSource": "remote",
                    "buildType": "app-bundle",
                },
            },
        },
        "submit": {
            "production": {
                "ios": {
                    "ascAppId": config.get("apple_app_id", ""),
                    "appleTeamId": config.get("apple_team_id", ""),
                },
                "android": {
                    "serviceAccountKeyPath": config.get(
                        "google_service_account_key", "./credentials/google-play-key.json"
                    ),
                    "track": config.get("android_track", "internal"),
                    "releaseStatus": config.get("android_release_status", "draft"),
                },
            },
        },
    }


def generate_package_json(
    app_name: str,
    bundle_id: str,
    mode: str,
    features: dict[str, bool],
) -> dict[str, Any]:
    """Generate package.json for the Expo project."""
    slug = app_name.lower().replace(" ", "-")

    deps: dict[str, str] = {
        "expo": "~52.0.0",
        "expo-status-bar": "~2.0.0",
        "react": "18.3.1",
        "react-native": "0.76.6",
        "react-native-web": "~0.19.13",
        "react-dom": "18.3.1",
        "expo-constants": "~17.0.0",
        "expo-asset": "~11.0.0",
        "expo-font": "~13.0.0",
        "@expo/metro-runtime": "~4.0.0",
    }

    if mode == "webview":
        deps["react-native-webview"] = "13.12.5"

    if features.get("deep_linking"):
        deps["expo-linking"] = "~7.0.0"
        deps["expo-router"] = "~4.0.0"

    if features.get("push_notifications"):
        deps["expo-notifications"] = "~0.29.0"
        deps["expo-device"] = "~7.0.0"

    if features.get("offline_support"):
        deps["expo-updates"] = "~0.26.0"
        deps["@react-native-async-storage/async-storage"] = "2.1.0"

    return {
        "name": slug,
        "version": "1.0.0",
        "main": "node_modules/expo/AppEntry.js",
        "scripts": {
            "start": "expo start",
            "android": "expo start --android",
            "ios": "expo start --ios",
            "web": "expo start --web",
            "build:ios": "eas build --platform ios --profile production",
            "build:android": "eas build --platform android --profile production",
            "build:all": "eas build --platform all --profile production",
            "submit:ios": "eas submit --platform ios --profile production",
            "submit:android": "eas submit --platform android --profile production",
            "submit:all": "eas submit --platform all --profile production",
            "deploy": "npm run build:all && npm run submit:all",
        },
        "dependencies": deps,
        "devDependencies": {
            "@babel/core": "^7.24.0",
            "@types/react": "~18.3.0",
            "typescript": "~5.3.0",
        },
        "private": True,
    }
