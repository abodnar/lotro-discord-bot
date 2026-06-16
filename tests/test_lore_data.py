import json
import lore_data
from lore_data import load_version_info


def test_load_version_info_with_version(tmp_path, monkeypatch):
    f = tmp_path / "version.json"
    f.write_text(json.dumps({"version": "48.5"}))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(f))
    assert load_version_info() == {"version": "48.5"}


def test_load_version_info_with_date(tmp_path, monkeypatch):
    f = tmp_path / "version.json"
    f.write_text(json.dumps({"fetched_date": "2026-06-15"}))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(f))
    assert load_version_info() == {"fetched_date": "2026-06-15"}


def test_load_version_info_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(tmp_path / "nonexistent.json"))
    assert load_version_info() == {}


def test_load_version_info_invalid_json(tmp_path, monkeypatch):
    f = tmp_path / "version.json"
    f.write_text("not valid json{{{")
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(f))
    assert load_version_info() == {}
