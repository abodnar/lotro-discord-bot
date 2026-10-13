import os

import pytest

import lore_data
import lore_db
from cogs import treasure_cog

CONTAINERS_XML = """<containers>
  <container id="c1" name="Wooden Chest" trophyListId="t1" treasureListId="tr1"/>
  <container id="c2" name="Wooden Chest" trophyListId="t1" treasureListId="tr1"/>
  <container id="c3" name="Class Chest" filteredTrophyTableId="f1"/>
</containers>"""

LOOTS_XML = """<loots>
  <trophyList id="t1">
    <trophyListEntry name="Sword" dropFrequency="1.0"/>
    <trophyListEntry treasureGroupProfileId="i1" dropFrequency="0.5"/>
  </trophyList>
  <trophyList id="t2">
    <trophyListEntry name="Captain Helm" dropFrequency="1.0"/>
  </trophyList>
  <itemsTable id="i1">
    <itemsTableEntry name="Gem" weight="1"/>
    <itemsTableEntry name="Coin" quantity="5" weight="3"/>
  </itemsTable>
  <treasureList id="tr1">
    <treasureListEntry treasureGroupProfileId="i1"/>
  </treasureList>
  <filteredTrophyTable id="f1">
    <filteredTrophyTableEntry requiredClass="Captain" minLevel="50" trophyListId="t2"/>
  </filteredTrophyTable>
</loots>"""


@pytest.fixture
def lore_dir(tmp_path, monkeypatch):
    (tmp_path / "containers.xml").write_text(CONTAINERS_XML)
    (tmp_path / "loots.xml").write_text(LOOTS_XML)
    monkeypatch.setattr(lore_data, 'LORE_DIR', str(tmp_path))
    monkeypatch.setattr(lore_data, 'VERSION_FILE', str(tmp_path / "version.json"))
    yield tmp_path
    if treasure_cog.lore is not None:
        treasure_cog.lore.close()
        treasure_cog.lore = None


def test_load_builds_database_and_container_names(lore_dir):
    assert treasure_cog.load_lore_data() is True
    assert (lore_dir / "lore.db").exists()
    assert treasure_cog.containers == {"c1": "Wooden Chest", "c2": "Wooden Chest", "c3": "Class Chest"}
    assert treasure_cog.containers_unique == {"c1": "Wooden Chest", "c3": "Class Chest"}


def test_load_without_files_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(lore_data, 'LORE_DIR', str(tmp_path))
    assert treasure_cog.load_lore_data() is False


def test_load_reuses_fresh_database(lore_dir, monkeypatch):
    treasure_cog.load_lore_data()
    monkeypatch.setattr(lore_db, 'build', lambda *a: pytest.fail("rebuilt a fresh database"))
    assert treasure_cog.load_lore_data() is True


def test_load_rebuilds_when_xml_is_newer(lore_dir):
    treasure_cog.load_lore_data()
    (lore_dir / "loots.xml").write_text(LOOTS_XML.replace("Sword", "Axe"))
    db_mtime = os.path.getmtime(lore_dir / "lore.db")
    os.utime(lore_dir / "loots.xml", (db_mtime + 10, db_mtime + 10))
    treasure_cog.load_lore_data()
    assert treasure_cog.compute_loot("c1", "Captain", 160, False)[0] == [100.0, ["100% -- Axe"]]


def test_compute_loot_resolves_trophy_and_treasure_lists(lore_dir):
    treasure_cog.load_lore_data()
    assert treasure_cog.compute_loot("c1", "Captain", 160, False) == [
        [100.0, ["100% -- Sword"]],
        [50.0, ["75.00% -- 5 Coin", "25.00% -- Gem"]],
        [-1, ["75.00% -- 5 Coin", "25.00% -- Gem"]],
    ]


def test_compute_loot_filters_by_class_and_level(lore_dir):
    treasure_cog.load_lore_data()
    assert treasure_cog.compute_loot("c3", "Captain", 60, False) == [[100.0, ["100% -- Captain Helm"]]]
    assert treasure_cog.compute_loot("c3", "Captain", 40, False) == []
    assert treasure_cog.compute_loot("c3", "Hunter", 60, False) == []
