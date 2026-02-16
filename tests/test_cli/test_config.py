import pytest
import yaml
from pathlib import Path
from cli.utils.config import load_config, generate_default_config

def test_generate_default_config():
    config = generate_default_config(
        app_name="Test App",
        bundle_id="com.test.app",
        source_path="/path/to/source",
        output_path="/path/to/output"
    )
    
    assert config["app_name"] == "Test App"
    assert config["bundle_id"] == "com.test.app"
    assert config["platform"] == "both"
    assert "features" in config

def test_load_config(tmp_path):
    config_file = tmp_path / "autodeploy.yaml"
    config_data = {
        "app_name": "Test App",
        "bundle_id": "com.test.app",
        "source_path": str(tmp_path / "src"),
        "output_path": str(tmp_path / "out")
    }
    
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
        
    loaded = load_config(str(config_file))
    assert loaded["app_name"] == "Test App"
    assert loaded["bundle_id"] == "com.test.app"

def test_load_nonexistent_config():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")
