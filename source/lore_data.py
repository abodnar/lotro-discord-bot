import json
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RAW_BASE_URL = 'https://raw.githubusercontent.com/LotroCompanion/lotro-data/master/lore/'
COMMITS_API_URL = 'https://api.github.com/repos/LotroCompanion/lotro-data/commits'
UPDATE_MSG_RE = re.compile(r'Updated for Update ([\d.]+)')
LORE_FILES = ['containers.xml', 'loots.xml']
LORE_DIR = '../data/lore'
VERSION_FILE = os.path.join(LORE_DIR, 'version.json')


async def fetch_lore_data(session):
    """Download lore XML files from lotro-data and resolve a version label.

    Both files are downloaded to `<name>.tmp` first. Only if both downloads
    succeed are they moved into place and version.json written, so a failed
    or partial download raises without touching any existing files. Any
    .tmp files created before the failure are cleaned up automatically.
    """
    os.makedirs(LORE_DIR, exist_ok=True)

    tmp_paths = []
    try:
        for filename in LORE_FILES:
            dest = os.path.join(LORE_DIR, filename)
            tmp = dest + '.tmp'
            await _download_file(session, RAW_BASE_URL + filename, tmp)
            tmp_paths.append((tmp, dest))

        version_info = await _resolve_version(session)

        for tmp, dest in tmp_paths:
            os.replace(tmp, dest)
        with open(VERSION_FILE, 'w') as f:
            json.dump(version_info, f)

        return version_info
    except Exception:
        for tmp, _ in tmp_paths:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass
        raise


async def check_and_update_lore(session):
    """Re-fetch lore data if the resolved version differs from what's stored.

    Only triggers a download when a version label was actually resolved (not
    the fetch-date fallback), since the fallback can't be reliably compared
    across runs and would otherwise cause a re-download on every check.
    Returns the new version_info if a download was applied, or None if the
    data was already current or the version couldn't be resolved.
    """
    latest = await _resolve_version(session)
    if 'version' not in latest or latest == load_version_info():
        return None
    return await fetch_lore_data(session)


async def _download_file(session, url, dest_path):
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(dest_path, 'wb') as f:
            async for chunk in resp.content.iter_chunked(65536):
                f.write(chunk)


async def _resolve_version(session):
    """Resolve a version label from the commit history of the lore/ path.

    Tags on the upstream repo lag behind master, so the version is instead
    read from the most recent "Updated for Update X.Y" commit message
    touching lore/ — that's what actually produced the data being fetched.
    """
    try:
        params = {'path': 'lore', 'per_page': 30}
        async with session.get(COMMITS_API_URL, params=params) as resp:
            resp.raise_for_status()
            commits = await resp.json()
        for commit in commits:
            match = UPDATE_MSG_RE.search(commit['commit']['message'])
            if match:
                return {'version': match.group(1)}
        raise ValueError("No 'Updated for Update' commit found in recent history")
    except Exception as e:
        logger.warning(f"Could not resolve lore data version from commit history, using fetch date: {e}")
        return {'fetched_date': datetime.now().strftime('%Y-%m-%d')}


def load_version_info():
    try:
        with open(VERSION_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
