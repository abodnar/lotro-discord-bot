import os
import xml.etree.ElementTree as ET

import pytest

from lore_db import LoreDB, build

CONTAINERS_XML = """<containers>
  <container id="c1" name="Wooden Chest" trophyListId="t1"/>
  <container id="c2" name="Iron Chest" treasureListId="tr1"/>
</containers>"""

LOOTS_XML = """<loots>
  <trophyList id="t1">
    <trophyListEntry name="Sword" dropFrequency="1.0"/>
    <trophyListEntry name="Shield" quantity="2" dropFrequency="0.5"/>
  </trophyList>
  <itemsTable id="t1">
    <itemsTableEntry name="Gem" weight="3"/>
  </itemsTable>
  <treasureList id="tr1"/>
</loots>"""


@pytest.fixture
def lore_files(tmp_path):
    containers = tmp_path / "containers.xml"
    loots = tmp_path / "loots.xml"
    containers.write_text(CONTAINERS_XML)
    loots.write_text(LOOTS_XML)
    return containers, loots, tmp_path / "lore.db"


@pytest.fixture
def db(lore_files):
    build(*lore_files)
    lore = LoreDB(lore_files[2])
    yield lore
    lore.close()


def test_container_returns_attributes(db):
    assert db.container("c1") == {"id": "c1", "name": "Wooden Chest", "trophyListId": "t1"}


def test_container_unknown_id_returns_none(db):
    assert db.container("nope") is None


def test_containers_in_document_order(db):
    assert [c["id"] for c in db.containers()] == ["c1", "c2"]


def test_entries_returns_child_attributes_in_order(db):
    assert db.entries("trophyList", "t1") == [
        {"name": "Sword", "dropFrequency": "1.0"},
        {"name": "Shield", "quantity": "2", "dropFrequency": "0.5"},
    ]


def test_entries_kept_separate_per_kind(db):
    assert db.entries("itemsTable", "t1") == [{"name": "Gem", "weight": "3"}]


def test_entries_empty_table_returns_empty_list(db):
    assert db.entries("treasureList", "tr1") == []


def test_entries_unknown_id_returns_none(db):
    assert db.entries("trophyList", "nope") is None


def test_build_failure_keeps_existing_db(lore_files):
    containers, loots, db_path = lore_files
    build(containers, loots, db_path)
    loots.write_text("<loots><trophyList id='t2'>")
    with pytest.raises(ET.ParseError):
        build(containers, loots, db_path)
    lore = LoreDB(db_path)
    assert lore.entries("trophyList", "t1") is not None
    lore.close()
    assert sorted(os.listdir(db_path.parent)) == ["containers.xml", "loots.xml", "lore.db"]


def test_build_missing_file_raises(lore_files):
    containers, loots, db_path = lore_files
    loots.unlink()
    with pytest.raises(FileNotFoundError):
        build(containers, loots, db_path)
    assert not db_path.exists()
