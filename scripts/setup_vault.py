"""
Vault setup script to initialize the secure storage with provided credentials.
"""

import os
import json
from pathlib import Path
from cli.utils.credentials import CredentialManager

def setup_vault():
    print("Initializing Vault...")
    vault_dir = Path("/home/ubuntu/auto-deploy-stores/vault")
    cm = CredentialManager(vault_dir=vault_dir)
    
    # 1. Integrate Google Play Service Account
    google_json_path = "/home/ubuntu/upload/private-gpu-service-account.json"
    if os.path.exists(google_json_path):
        print(f"Storing Google Service Account from {google_json_path}")
        cm.store_credential_file(
            name="google_service_account",
            credential_type="google_service_account",
            file_path=google_json_path,
            metadata={
                "project_id": "private-gpu",
                "client_email": "goggle-analytics-personal@private-gpu.iam.gserviceaccount.com"
            }
        )
        print("✓ Google Play credentials integrated.")
    else:
        print("⚠ Google Service Account file not found.")

    # 2. Integrate Apple credentials if available in environment/reference
    # For now, we'll look for placeholders or environment variables
    apple_key_id = os.environ.get("APPLE_KEY_ID")
    apple_issuer_id = os.environ.get("APPLE_ISSUER_ID")
    apple_key_content = os.environ.get("APPLE_KEY_CONTENT")
    
    if apple_key_id and apple_issuer_id and apple_key_content:
        cm.store_credential(
            name="apple_api_key",
            credential_type="apple_api_key",
            value=json.dumps({
                "key_id": apple_key_id,
                "issuer_id": apple_issuer_id,
                "key_content": apple_key_content
            })
        )
        print("✓ Apple credentials integrated.")

    print("Vault initialization complete.")

if __name__ == "__main__":
    setup_vault()
