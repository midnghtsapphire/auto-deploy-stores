import os
import json
import shutil
import pytest
from pathlib import Path
from cli.utils.credentials import CredentialManager

@pytest.fixture
def temp_vault(tmp_path):
    vault_dir = tmp_path / "vault"
    return vault_dir

def test_store_and_get_credential(temp_vault):
    cm = CredentialManager(vault_dir=temp_vault, master_key="test-key")
    
    # Test string credential
    cm.store_credential("test_cred", "custom", "secret-value")
    cred = cm.get_credential("test_cred")
    
    assert cred["name"] == "test_cred"
    assert cred["value"] == "secret-value"
    assert cred["is_file"] is False

def test_store_and_get_file_credential(temp_vault, tmp_path):
    cm = CredentialManager(vault_dir=temp_vault, master_key="test-key")
    
    # Create a dummy file
    dummy_file = tmp_path / "test.json"
    dummy_content = {"key": "value"}
    dummy_file.write_text(json.dumps(dummy_content))
    
    # Test file credential
    cm.store_credential_file("test_file_cred", "google_service_account", str(dummy_file))
    cred = cm.get_credential("test_file_cred")
    
    assert cred["name"] == "test_file_cred"
    assert cred["is_file"] is True
    assert Path(cred["key_path"]).exists()
    
    # Verify content
    with open(cred["key_path"], "r") as f:
        content = json.load(f)
    assert content == dummy_content

def test_list_credentials(temp_vault):
    cm = CredentialManager(vault_dir=temp_vault, master_key="test-key")
    cm.store_credential("cred1", "type1", "val1")
    cm.store_credential("cred2", "type2", "val2")
    
    creds = cm.list_credentials()
    assert len(creds) == 2
    names = [c["name"] for c in creds]
    assert "cred1" in names
    assert "cred2" in names

def test_remove_credential(temp_vault):
    cm = CredentialManager(vault_dir=temp_vault, master_key="test-key")
    cm.store_credential("to_remove", "type", "val")
    assert cm.has_credential("to_remove")
    
    cm.remove_credential("to_remove")
    assert not cm.has_credential("to_remove")
