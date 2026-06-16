import xml.etree.ElementTree as ET

from cogs.treasure_cog import _build_unique_containers, _dedup_loot, formatNumber, override_player_class


def _make_container(id_, name, **attrs):
    el = ET.Element('container')
    el.attrib['id'] = id_
    el.attrib['name'] = name
    el.attrib.update(attrs)
    return el


def _make_root(*containers):
    root = ET.Element('containers')
    for c in containers:
        root.append(c)
    return root


class TestFormatNumber:
    def test_above_0_1_uses_two_decimals(self):
        assert formatNumber(50.0) == "50.00"
        assert formatNumber(0.11) == "0.11"

    def test_above_0_01_uses_three_decimals(self):
        assert formatNumber(0.05) == "0.050"
        assert formatNumber(0.011) == "0.011"

    def test_very_small_uses_four_decimals(self):
        assert formatNumber(0.005) == "0.0050"
        assert formatNumber(0.001) == "0.0010"


class TestOverridePlayerClass:
    def test_loremaster(self):
        assert override_player_class("Loremaster") == "Lore-master"

    def test_mariner(self):
        assert override_player_class("Mariner") == "Corsair"

    def test_runekeeper(self):
        assert override_player_class("Runekeeper") == "Rune-keeper"

    def test_passthrough(self):
        assert override_player_class("Captain") == "Captain"
        assert override_player_class("Hunter") == "Hunter"
        assert override_player_class("Guardian") == "Guardian"


class TestDedupLoot:
    def test_removes_exact_duplicate(self):
        loot = [
            [50.0, ["50.00% -- Some Item"]],
            [50.0, ["50.00% -- Some Item"]],
        ]
        assert len(_dedup_loot(loot)) == 1

    def test_keeps_different_items(self):
        loot = [
            [50.0, ["50.00% -- Item A"]],
            [50.0, ["50.00% -- Item B"]],
        ]
        assert len(_dedup_loot(loot)) == 2

    def test_keeps_same_name_different_frequency(self):
        loot = [
            [50.0, ["50.00% -- Item A"]],
            [25.0, ["25.00% -- Item A"]],
        ]
        assert len(_dedup_loot(loot)) == 2

    def test_empty_loot(self):
        assert _dedup_loot([]) == []

    def test_preserves_order_of_first_occurrence(self):
        loot = [
            [50.0, ["50.00% -- Item A"]],
            [25.0, ["25.00% -- Item B"]],
            [50.0, ["50.00% -- Item A"]],  # duplicate
            [10.0, ["10.00% -- Item C"]],
        ]
        result = _dedup_loot(loot)
        assert len(result) == 3
        assert result[0][0] == 50.0
        assert result[1][0] == 25.0
        assert result[2][0] == 10.0


class TestBuildUniqueContainers:
    def test_deduplicates_identical_loot_tables(self):
        c1 = _make_container("id1", "Wooden Chest", trophyListId="t1", treasureListId="tr1")
        c2 = _make_container("id2", "Wooden Chest", trophyListId="t1", treasureListId="tr1")
        root = _make_root(c1, c2)
        all_containers = {"id1": "Wooden Chest", "id2": "Wooden Chest"}

        result = _build_unique_containers(root, all_containers)
        assert len(result) == 1
        assert "id1" in result

    def test_keeps_same_name_different_loot_tables(self):
        c1 = _make_container("id1", "Wooden Chest", trophyListId="t1", treasureListId="tr1")
        c2 = _make_container("id2", "Wooden Chest", trophyListId="t2", treasureListId="tr2")
        root = _make_root(c1, c2)
        all_containers = {"id1": "Wooden Chest", "id2": "Wooden Chest"}

        result = _build_unique_containers(root, all_containers)
        assert len(result) == 2

    def test_keeps_different_names_same_loot_table(self):
        c1 = _make_container("id1", "Wooden Chest", trophyListId="t1")
        c2 = _make_container("id2", "Iron Chest", trophyListId="t1")
        root = _make_root(c1, c2)
        all_containers = {"id1": "Wooden Chest", "id2": "Iron Chest"}

        result = _build_unique_containers(root, all_containers)
        assert len(result) == 2

    def test_skips_ids_absent_from_all_containers(self):
        c1 = _make_container("id1", "Wooden Chest")
        c2 = _make_container("id2", "Iron Chest")
        root = _make_root(c1, c2)
        all_containers = {"id1": "Wooden Chest"}

        result = _build_unique_containers(root, all_containers)
        assert len(result) == 1
        assert "id2" not in result
