import json

import pytest

import lore_data
from lore_data import load_version_info, _resolve_version, check_and_update_lore


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


class FakeDownloadResponse:
    def raise_for_status(self):
        pass

    @property
    def content(self):
        return self

    def iter_chunked(self, size):
        async def gen():
            yield b'<data/>'
        return gen()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeUpdateSession:
    """Serves commit history from the commits API and dummy bytes for file downloads."""

    def __init__(self, commits):
        self._commits = commits

    def get(self, url, params=None):
        if url == lore_data.COMMITS_API_URL:
            return FakeResponse(self._commits)
        return FakeDownloadResponse()


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


@pytest.mark.asyncio
async def test_check_and_update_lore_downloads_on_new_version(tmp_path, monkeypatch):
    monkeypatch.setattr(lore_data, 'LORE_DIR', str(tmp_path))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(tmp_path / 'version.json'))
    (tmp_path / 'version.json').write_text(json.dumps({'version': '48.5'}))
    session = FakeUpdateSession([{'commit': {'message': 'Updated for Update 49.1'}}])

    result = await check_and_update_lore(session)

    assert result == {'version': '49.1'}
    assert load_version_info() == {'version': '49.1'}
    assert (tmp_path / 'containers.xml').read_bytes() == b'<data/>'


@pytest.mark.asyncio
async def test_check_and_update_lore_skips_when_version_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(lore_data, 'LORE_DIR', str(tmp_path))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(tmp_path / 'version.json'))
    (tmp_path / 'version.json').write_text(json.dumps({'version': '49.1'}))
    session = FakeUpdateSession([{'commit': {'message': 'Updated for Update 49.1'}}])

    result = await check_and_update_lore(session)

    assert result is None
    assert not (tmp_path / 'containers.xml').exists()


@pytest.mark.asyncio
async def test_check_and_update_lore_skips_when_version_unresolved(tmp_path, monkeypatch):
    monkeypatch.setattr(lore_data, 'LORE_DIR', str(tmp_path))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(tmp_path / 'version.json'))
    (tmp_path / 'version.json').write_text(json.dumps({'version': '49.1'}))
    session = FakeUpdateSession([{'commit': {'message': 'Typo fix (French)'}}])

    result = await check_and_update_lore(session)

    assert result is None
    assert not (tmp_path / 'containers.xml').exists()
