import copy
import yaml
import pytest
import config_loader

@pytest.fixture(autouse=True)
def reset_config():
    # Reset the global CONFIG before each test
    config_loader.CONFIG = config_loader.DEFAULT_CONFIG.copy()


def test_load_config_none(tmp_path):
    cfg_file = tmp_path / "empty.yaml"
    cfg_file.write_text("")
    config_loader.load_config(str(cfg_file))
    assert config_loader.CONFIG == config_loader.DEFAULT_CONFIG


def test_load_config_not_dict(tmp_path, capsys):
    cfg_file = tmp_path / "list.yaml"
    cfg_file.write_text("- 1\n- 2\n")
    config_loader.load_config(str(cfg_file))
    captured = capsys.readouterr()
    assert "not a dictionary" in captured.out
    assert config_loader.CONFIG == config_loader.DEFAULT_CONFIG


def test_load_config_parse_error(tmp_path, capsys):
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text("foo: [")
    config_loader.load_config(str(cfg_file))
    captured = capsys.readouterr()
    assert "Error parsing YAML" in captured.out
    assert config_loader.CONFIG == config_loader.DEFAULT_CONFIG

def test_load_config_merges(tmp_path):
    # prepare temporary config file
    cfg = {
        "mqtt": {"broker": "example.com", "port": 9999},
        "dashboard": {"enable": False},
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg))

    # reset config to defaults before loading
    config_loader.CONFIG = copy.deepcopy(config_loader.DEFAULT_CONFIG)
    config_loader.load_config(str(cfg_path))

    assert config_loader.CONFIG["mqtt"]["broker"] == "example.com"
    assert config_loader.CONFIG["mqtt"]["port"] == 9999
    assert config_loader.CONFIG["dashboard"]["enable"] is False
    # default config should remain unchanged
    assert config_loader.DEFAULT_CONFIG["dashboard"]["enable"] is True