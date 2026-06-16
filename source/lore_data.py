import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RAW_BASE_URL = 'https://raw.githubusercontent.com/LotroCompanion/lotro-data/master/lore/'
TAGS_API_URL = 'https://api.github.com/repos/LotroCompanion/lotro-data/tags'
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


async def _download_file(session, url, dest_path):
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(dest_path, 'wb') as f:
            async for chunk in resp.content.iter_chunked(65536):
                f.write(chunk)


async def _resolve_version(session):
    try:
        async with session.get(TAGS_API_URL) as resp:
            resp.raise_for_status()
            tags = await resp.json()
        parts = tags[0]['name'].split('.')
        version = '.'.join(parts[3:])
        if not version:
            raise ValueError(f"Unexpected tag format: {tags[0]['name']}")
        return {'version': version}
    except Exception as e:
        logger.warning(f"Could not resolve lore data version from tags, using fetch date: {e}")
        return {'fetched_date': datetime.now().strftime('%Y-%m-%d')}


def load_version_info():
    try:
        with open(VERSION_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
