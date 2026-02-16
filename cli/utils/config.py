"""
Configuration management for auto-deploy-stores.

Handles loading, validating, and generating configuration files.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate, ValidationError


CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["app_name", "bundle_id", "source_path", "output_path"],
    "properties": {
        "app_name": {"type": "string", "minLength": 1},
        "bundle_id": {
            "type": "string",
            "pattern": r"^[a-zA-Z][a-zA-Z0-9]*(\.[a-zA-Z][a-zA-Z0-9]*)+$",
        },
        "source_path": {"type": "string"},
        "output_path": {"type": "string"},
        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "build_number": {"type": "string"},
        "version_code": {"type": "integer", "minimum": 1},
        "platform": {"type": "string", "enum": ["ios", "android", "both"]},
        "wrap_mode": {"type": "string", "enum": ["webview", "hybrid", "native"]},
        "splash_background": {"type": "string"},
        "icon_background": {"type": "string"},
        "eas_project_id": {"type": "string"},
        "apple_app_id": {"type": "string"},
        "apple_team_id": {"type": "string"},
        "google_service_account_key": {"type": "string"},
        "android_keystore_path": {"type": "string"},
        "android_track": {
            "type": "string",
            "enum": ["internal", "alpha", "beta", "production"],
        },
        "android_release_status": {
            "type": "string",
            "enum": ["draft", "completed", "halted", "inProgress"],
        },
        "features": {
            "type": "object",
            "properties": {
                "deep_linking": {"type": "boolean"},
                "push_notifications": {"type": "boolean"},
                "offline_support": {"type": "boolean"},
            },
        },
        "environments": {
            "type": "object",
            "properties": {
                "dev": {"type": "object"},
                "test": {"type": "object"},
                "live": {"type": "object"},
            },
        },
    },
}


def load_config(config_path: str = "autodeploy.yaml") -> dict[str, Any]:
    """Load and validate configuration from YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Validated configuration dictionary.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValidationError: If the config doesn't match the schema.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Run 'autodeploy init' to create one."
        )

    with open(path) as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Empty configuration file: {config_path}")

    # Expand environment variables in string values
    config = _expand_env_vars(config)

    # Validate against schema
    try:
        validate(instance=config, schema=CONFIG_SCHEMA)
    except ValidationError as e:
        raise ValidationError(
            f"Invalid configuration: {e.message}\n"
            f"Path: {'.'.join(str(p) for p in e.absolute_path)}"
        )

    return config


def generate_default_config(
    app_name: str,
    bundle_id: str,
    source_path: str,
    output_path: str,
    platform: str = "both",
) -> dict[str, Any]:
    """Generate a default configuration dictionary.

    Args:
        app_name: Display name of the app.
        bundle_id: Unique bundle identifier.
        source_path: Path to the React/Vite source.
        output_path: Output directory for the Expo project.
        platform: Target platform(s).

    Returns:
        Default configuration dictionary.
    """
    return {
        "app_name": app_name,
        "bundle_id": bundle_id,
        "source_path": source_path,
        "output_path": output_path,
        "version": "1.0.0",
        "build_number": "1",
        "version_code": 1,
        "platform": platform,
        "wrap_mode": "webview",
        "splash_background": "#ffffff",
        "icon_background": "#ffffff",
        "eas_project_id": "",
        "apple_app_id": "",
        "apple_team_id": "",
        "google_service_account_key": "./credentials/google-play-key.json",
        "android_keystore_path": "",
        "android_track": "internal",
        "android_release_status": "draft",
        "features": {
            "deep_linking": True,
            "push_notifications": True,
            "offline_support": True,
        },
        "environments": {
            "dev": {
                "eas_profile": "development",
                "android_track": "internal",
            },
            "test": {
                "eas_profile": "preview",
                "android_track": "alpha",
            },
            "live": {
                "eas_profile": "production",
                "android_track": "production",
            },
        },
    }


def _expand_env_vars(config: dict[str, Any]) -> dict[str, Any]:
    """Recursively expand environment variables in config values."""
    expanded: dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, str):
            expanded[key] = os.path.expandvars(value)
        elif isinstance(value, dict):
            expanded[key] = _expand_env_vars(value)
        else:
            expanded[key] = value
    return expanded
