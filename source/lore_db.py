"""SQLite store for the LotroCompanion lore XML.

Holding the parsed loots.xml tree in memory costs ~100 MB, so the XML is
streamed into a small SQLite file instead and looked up by id on demand.
Both files are flat: a root of id-keyed elements, each holding attribute-only
child entries. Attributes are stored as JSON so callers get plain dicts.
"""
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA = """
CREATE TABLE containers (seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, attrs TEXT NOT NULL);
CREATE TABLE loot_tables (kind TEXT NOT NULL, id TEXT NOT NULL, entries TEXT NOT NULL,
                          PRIMARY KEY (kind, id)) WITHOUT ROWID;
"""


def _iter_tables(path):
    """Yield (tag, attrs, [child attrs]) for each top-level element, without keeping the tree."""
    depth = 0
    entries = []
    root = None
    for event, elem in ET.iterparse(path, events=('start', 'end')):
        if event == 'start':
            depth += 1
            if depth == 1:
                root = elem
            continue
        depth -= 1
        if depth == 2:
            entries.append(dict(elem.attrib))
        elif depth == 1:
            yield elem.tag, dict(elem.attrib), entries
            entries = []
            root.clear()


def build(containers_xml, loots_xml, db_path):
    """Build the lore database from the XML files, replacing db_path atomically.

    Raises FileNotFoundError or ET.ParseError on missing or malformed input,
    leaving any existing database untouched.
    """
    tmp = str(db_path) + '.tmp'
    if os.path.exists(tmp):
        os.remove(tmp)
    try:
        conn = sqlite3.connect(tmp)
        try:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT INTO containers (id, attrs) VALUES (?, ?)",
                ((attrs['id'], json.dumps(attrs)) for _tag, attrs, _entries in _iter_tables(containers_xml)))
            conn.executemany(
                "INSERT INTO loot_tables (kind, id, entries) VALUES (?, ?, ?)",
                ((tag, attrs['id'], json.dumps(entries)) for tag, attrs, entries in _iter_tables(loots_xml)))
            conn.commit()
        finally:
            conn.close()
        os.replace(tmp, db_path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


class LoreDB:
    """Read-only lookups into a database written by build()."""

    def __init__(self, db_path):
        uri = Path(db_path).absolute().as_uri() + '?mode=ro'
        # Opened in the executor thread that (re)loads lore data, queried from the event loop.
        self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)

    def close(self):
        self._conn.close()

    def container(self, container_id):
        row = self._conn.execute("SELECT attrs FROM containers WHERE id = ?", (container_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def containers(self):
        return [json.loads(attrs) for (attrs,) in self._conn.execute("SELECT attrs FROM containers ORDER BY seq")]

    def entries(self, kind, table_id):
        row = self._conn.execute(
            "SELECT entries FROM loot_tables WHERE kind = ? AND id = ?", (kind, table_id)).fetchone()
        return json.loads(row[0]) if row else None
