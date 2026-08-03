import json

import pytest

import lore_data
from lore_data import load_version_info, _resolve_version


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, params=None):
        return FakeResponse(self._payload)


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


@pytest.mark.asyncio
async def test_resolve_version_finds_update_commit():
    commits = [
        {'commit': {'message': 'Added "UI filter" for deeds'}},
        {'commit': {'message': 'Updated for Update 49.1'}},
        {'commit': {'message': 'Updated for Update 48.8'}},
    ]
    session = FakeSession(commits)
    assert await _resolve_version(session) == {'version': '49.1'}


@pytest.mark.asyncio
async def test_resolve_version_skips_unrelated_commits():
    commits = [
        {'commit': {'message': 'Typo fix (French)'}},
        {'commit': {'message': 'Update of Russian labels (v335 ; Update 48.8)'}},
        {'commit': {'message': 'Updated for Update 48.8'}},
    ]
    session = FakeSession(commits)
    assert await _resolve_version(session) == {'version': '48.8'}


@pytest.mark.asyncio
async def test_resolve_version_falls_back_to_date_when_no_match(monkeypatch):
    session = FakeSession([{'commit': {'message': 'Typo fix (French)'}}])
    monkeypatch.setattr(lore_data, 'datetime', _FixedDatetime)
    assert await _resolve_version(session) == {'fetched_date': '2026-08-03'}


@pytest.mark.asyncio
async def test_resolve_version_falls_back_to_date_on_request_error(monkeypatch):
    class FailingSession:
        def get(self, url, params=None):
            raise ConnectionError("boom")

    monkeypatch.setattr(lore_data, 'datetime', _FixedDatetime)
    assert await _resolve_version(FailingSession()) == {'fetched_date': '2026-08-03'}


class _FixedDatetime:
    @classmethod
    def now(cls):
        import datetime as _dt
        return _dt.datetime(2026, 8, 3)
