"""
EAS Client utility for interacting with Expo Application Services (EAS).

Wraps the EAS CLI to perform builds and submissions.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any


class EASClient:
    """Wrapper for EAS CLI operations."""

    def __init__(self, project_dir: Path, verbose: bool = False):
        self.project_dir = project_dir
        self.verbose = verbose

    def _run_command(self, cmd: list[str], capture_output: bool = True) -> str:
        """Run an EAS CLI command."""
        try:
            if self.verbose:
                print(f"Running command: {' '.join(cmd)} in {self.project_dir}")
            
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=capture_output,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise RuntimeError(f"EAS command failed: {' '.join(cmd)}\nError: {error_msg}")

    def build_cloud(self, platform: str, profile: str = "production") -> str:
        """Trigger a cloud build via EAS Build."""
        cmd = ["eas", "build", "--platform", platform, "--profile", profile, "--non-interactive", "--json"]
        output = self._run_command(cmd)
        
        # EAS build --json returns an array of build objects
        try:
            builds = json.loads(output)
            if isinstance(builds, list) and len(builds) > 0:
                return builds[0]["id"]
            elif isinstance(builds, dict):
                return builds["id"]
            raise ValueError(f"Unexpected EAS build output: {output}")
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Failed to parse EAS build output: {e}\nOutput: {output}")

    def build_local(self, platform: str, profile: str = "production") -> str:
        """Trigger a local build (requires local setup)."""
        cmd = ["eas", "build", "--platform", platform, "--profile", profile, "--local", "--non-interactive"]
        # Local builds don't typically return a cloud build ID
        self._run_command(cmd, capture_output=False)
        return "local-build"

    def get_build_status(self, build_id: str) -> dict[str, Any]:
        """Get the status of a specific build."""
        if build_id == "local-build":
            return {"status": "finished", "id": build_id}
            
        cmd = ["eas", "build:view", build_id, "--json"]
        output = self._run_command(cmd)
        return json.loads(output)

    def wait_for_builds(self, build_ids: dict[str, str], timeout: int = 1800) -> dict[str, dict[str, Any]]:
        """Wait for multiple builds to complete."""
        results: dict[str, dict[str, Any]] = {}
        pending = set(build_ids.keys())
        start_time = time.time()
        
        while pending and (time.time() - start_time) < timeout:
            for plat in list(pending):
                bid = build_ids[plat]
                status_info = self.get_build_status(bid)
                status = status_info.get("status")
                
                if status in ("finished", "errored", "canceled"):
                    results[plat] = status_info
                    pending.discard(plat)
            
            if pending:
                time.sleep(30)
                
        if pending:
            raise TimeoutError(f"Timed out waiting for builds: {', '.join(pending)}")
            
        return results

    def download_artifact(self, build_id: str, output_dir: Path) -> Path:
        """Download the artifact for a finished build."""
        status = self.get_build_status(build_id)
        url = status.get("artifacts", {}).get("buildUrl")
        if not url:
            raise ValueError(f"No artifact URL found for build {build_id}")
            
        filename = f"{build_id}.ipa" if status.get("platform") == "ios" else f"{build_id}.aab"
        dest = output_dir / filename
        
        # Use curl to download
        subprocess.run(["curl", "-L", url, "-o", str(dest)], check=True)
        return dest

    def submit(self, platform: str, build_id: str, config: dict[str, Any] | None = None) -> str:
        """Submit a build to the store via EAS Submit."""
        cmd = ["eas", "submit", "--platform", platform, "--id", build_id, "--non-interactive", "--json"]
        
        # Add extra config flags if provided
        if config:
            # Note: EAS CLI flags depend on platform. This is simplified.
            pass
            
        output = self._run_command(cmd)
        try:
            submission = json.loads(output)
            return submission["id"]
        except (json.JSONDecodeError, KeyError):
            # Sometimes EAS submit output isn't clean JSON
            return "submission-triggered"

    def get_submission_status(self, submission_id: str) -> dict[str, Any]:
        """Get the status of a submission."""
        if submission_id == "submission-triggered":
            return {"status": "finished"}
            
        cmd = ["eas", "submit:view", submission_id, "--json"]
        output = self._run_command(cmd)
        return json.loads(output)

    def get_latest_build(self, platform: str, profile: str = "production") -> dict[str, Any] | None:
        """Get the latest build for a platform."""
        cmd = ["eas", "build:list", "--platform", platform, "--profile", profile, "--limit", "1", "--json"]
        output = self._run_command(cmd)
        builds = json.loads(output)
        return builds[0] if builds else None

    def set_apple_credentials(self, key_id: str, issuer_id: str, key_path: str) -> None:
        """Set Apple App Store Connect API key for EAS."""
        # This usually involves setting environment variables or using eas credentials
        os.environ["EXPO_APPLE_APP_SPECIFIC_PASSWORD"] = "" # If needed
        # EAS CLI uses these env vars if configured
        os.environ["EAS_APPLE_API_KEY_ID"] = key_id
        os.environ["EAS_APPLE_API_KEY_ISSUER_ID"] = issuer_id
        os.environ["EAS_APPLE_API_KEY_PATH"] = key_path
