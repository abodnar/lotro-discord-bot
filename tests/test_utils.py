from utils import chunks, fp_ratio, get_match, get_partial_matches


class TestChunks:
    def test_splits_evenly(self):
        assert list(chunks([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]

    def test_last_chunk_smaller(self):
        assert list(chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]

    def test_empty_list(self):
        assert list(chunks([], 3)) == []

    def test_chunk_larger_than_list(self):
        assert list(chunks([1, 2], 5)) == [[1, 2]]

    def test_chunk_size_one(self):
        assert list(chunks([1, 2, 3], 1)) == [[1], [2], [3]]


class TestFpRatio:
    def test_identical_strings(self):
        assert fp_ratio("captain", "captain") == 100

    def test_empty_string_returns_zero(self):
        assert fp_ratio("", "captain") == 0

    def test_completely_different(self):
        assert fp_ratio("captain", "zzzzzzz") < 50

    def test_partial_match_scores_above_zero(self):
        assert fp_ratio("capt", "captain") > 0


class TestGetMatch:
    def test_exact_match(self):
        result, score = get_match("Captain", ["Captain", "Hunter", "Guardian"])
        assert result == "Captain"
        assert score == 100

    def test_fuzzy_match(self):
        result, score = get_match("captin", ["Captain", "Hunter", "Guardian"])
        assert result == "Captain"

    def test_no_match_below_cutoff(self):
        result, score = get_match("zzz", ["Captain", "Hunter", "Guardian"])
        assert result is None
        assert score is None

    def test_returns_closest_match(self):
        result, _ = get_match("hunt", ["Captain", "Hunter", "Guardian"])
        assert result == "Hunter"


class TestGetPartialMatches:
    def test_returns_matching_values(self):
        word_list = ["Wooden Chest", "Wooden Box", "Iron Chest", "Silver Box"]
        matches = get_partial_matches("wooden", word_list)
        assert "Wooden Chest" in matches
        assert "Wooden Box" in matches
        assert "Silver Box" not in matches

    def test_keys_mode_returns_dict_keys(self):
        d = {"id1": "Wooden Chest", "id2": "Iron Chest", "id3": "Silver Box"}
        keys = get_partial_matches("wooden", d, keys=True)
        assert "id1" in keys
        assert "id3" not in keys

    def test_respects_limit(self):
        word_list = [f"Wooden Item {i}" for i in range(50)]
        matches = get_partial_matches("wooden", word_list, score_cutoff=50, limit=5)
        assert len(matches) <= 5

    def test_no_match_returns_empty(self):
        matches = get_partial_matches("zzz", ["Captain", "Hunter"], score_cutoff=90)
        assert not matches
