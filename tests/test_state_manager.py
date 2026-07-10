import json

import pytest

import src.state_manager as state_manager_module
from src.state_manager import StateManager


def _raise_offline():
    raise OSError("offline")


def test_local_state_is_created_atomically_in_a_nested_directory(tmp_path, monkeypatch):
    state_path = tmp_path / "nested" / "state.json"
    monkeypatch.setattr(state_manager_module, "STATE_PATH", str(state_path))

    manager = StateManager(key="daily")
    manager.update_state("2026-07-09")

    assert json.loads(state_path.read_text())["daily"]["last_processed_date"] == "2026-07-09"
    assert not state_path.with_suffix(".json.tmp").exists()


def test_gcs_load_failure_is_not_treated_as_missing_state(monkeypatch):
    manager = StateManager.__new__(StateManager)
    manager.state_path = "gs://test-bucket/state.json"
    monkeypatch.setattr(state_manager_module.storage, "Client", _raise_offline)

    with pytest.raises(RuntimeError, match="Unable to load state"):
        manager._load_from_gcs()


def test_gcs_save_failure_is_propagated(monkeypatch):
    manager = StateManager.__new__(StateManager)
    manager.state_path = "gs://test-bucket/state.json"
    manager.state = {"default": {"last_processed_date": "2026-07-09"}}
    monkeypatch.setattr(state_manager_module.storage, "Client", _raise_offline)

    with pytest.raises(RuntimeError, match="Unable to save state"):
        manager._save_to_gcs()
