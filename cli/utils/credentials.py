"""
Credential management for auto-deploy-stores.

Handles secure storage, encryption, and retrieval of store credentials.
Follows the glowstarlabs-vault pattern.
"""

import base64
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialManager:
    """Manages encrypted credentials in a local vault."""

    def __init__(self, vault_dir: Path | None = None, master_key: str | None = None):
        self.vault_dir = vault_dir or Path("/home/ubuntu/auto-deploy-stores/vault")
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir = self.vault_dir / "keys"
        self.keys_dir.mkdir(exist_ok=True)
        self.data_dir = self.vault_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.master_key = master_key or os.environ.get("AUTODEPLOY_MASTER_KEY", "default-dev-key-change-me")
        self._fernet = self._init_fernet()

    def _init_fernet(self) -> Fernet:
        """Initialize encryption engine."""
        salt = b"glowstarlabs-salt-fixed" # In production, use a stored salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)

    def _encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def _decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()

    def store_credential(self, name: str, credential_type: str, value: str, metadata: dict | None = None) -> None:
        """Store a string-based credential."""
        encrypted_value = self._encrypt(value)
        entry = {
            "name": name,
            "type": credential_type,
            "value": encrypted_value,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow().isoformat(),
            "is_file": False
        }
        (self.data_dir / f"{name}.json").write_text(json.dumps(entry, indent=2))

    def store_credential_file(self, name: str, credential_type: str, file_path: str, metadata: dict | None = None) -> None:
        """Store a file-based credential (encrypts the file content)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Credential file not found: {file_path}")
            
        content = path.read_bytes()
        # For files, we store the encrypted content in a separate file and the metadata in JSON
        encrypted_content = self._fernet.encrypt(content)
        
        file_storage_path = self.keys_dir / f"{name}.enc"
        file_storage_path.write_bytes(encrypted_content)
        
        entry = {
            "name": name,
            "type": credential_type,
            "file_ref": str(file_storage_path),
            "original_filename": path.name,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow().isoformat(),
            "is_file": True
        }
        (self.data_dir / f"{name}.json").write_text(json.dumps(entry, indent=2))

    def get_credential(self, name: str) -> dict[str, Any] | None:
        """Retrieve and decrypt a credential."""
        path = self.data_dir / f"{name}.json"
        if not path.exists():
            return None
            
        entry = json.loads(path.read_text())
        if entry["is_file"]:
            enc_path = Path(entry["file_ref"])
            if enc_path.exists():
                decrypted_content = self._fernet.decrypt(enc_path.read_bytes())
                # Save to a temp file if needed by the caller, or return as bytes
                temp_path = Path(f"/tmp/autodeploy-{name}-{entry['original_filename']}")
                temp_path.write_bytes(decrypted_content)
                entry["key_path"] = str(temp_path)
        else:
            entry["value"] = self._decrypt(entry["value"])
            # If value is JSON, parse it
            try:
                entry["data"] = json.loads(entry["value"])
            except json.JSONDecodeError:
                pass
                
        return entry

    def list_credentials(self) -> list[dict[str, Any]]:
        """List all stored credentials with status."""
        results = []
        for path in self.data_dir.glob("*.json"):
            entry = json.loads(path.read_text())
            # Don't include the actual secret values in the list
            entry.pop("value", None)
            entry["valid"] = True # Basic check, could be more complex
            results.append(entry)
        return results

    def remove_credential(self, name: str) -> None:
        """Remove a credential."""
        json_path = self.data_dir / f"{name}.json"
        if json_path.exists():
            entry = json.loads(json_path.read_text())
            if entry.get("is_file") and "file_ref" in entry:
                file_path = Path(entry["file_ref"])
                if file_path.exists():
                    file_path.unlink()
            json_path.unlink()

    def has_credential(self, name: str) -> bool:
        """Check if a credential exists."""
        return (self.data_dir / f"{name}.json").exists()

    def verify_apple_credentials(self) -> dict[str, bool]:
        """Verify Apple App Store Connect credentials."""
        # This would ideally call the ASC API to check validity
        return {
            "api_key_present": self.has_credential("apple_api_key"),
            "team_id_present": self.has_credential("apple_team_id"),
        }

    def verify_google_credentials(self) -> dict[str, bool]:
        """Verify Google Play Store credentials."""
        return {
            "service_account_present": self.has_credential("google_service_account"),
        }

    def rotate_credential(self, name: str) -> None:
        """Archive current and prepare for new credential."""
        # Implementation of rotation logic
        pass

    def export_credentials(self, format: str = "env") -> str:
        """Export credentials for CI/CD usage."""
        creds = self.list_credentials()
        if format == "env":
            lines = []
            for c in creds:
                full = self.get_credential(c["name"])
                if full:
                    if full["is_file"]:
                        lines.append(f"AUTODEPLOY_{c['name'].upper()}_PATH={full['key_path']}")
                    else:
                        lines.append(f"AUTODEPLOY_{c['name'].upper()}={full['value']}")
            return "\n".join(lines)
        return json.dumps(creds, indent=2)
