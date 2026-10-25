from pathlib import Path

import pytest
import yaml

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.yaml"


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """A writable config.yaml (copy of the example) that get_config() will read."""
    path = tmp_path / "config.yaml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr("app.config.CONFIG_CANDIDATES", (path,))
    return path


@pytest.fixture
def edit_config(config_file):
    def edit(mutator):
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        mutator(data)
        config_file.write_text(yaml.safe_dump(data), encoding="utf-8")

    return edit
