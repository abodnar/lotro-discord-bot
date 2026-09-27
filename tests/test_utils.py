from utils import button_row, chunks, exceeds_max_future_offset, format_player_entry, fp_ratio, get_match, get_partial_matches


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


class TestButtonRow:
    def test_first_four_share_row(self):
        assert [button_row(i) for i in range(4)] == [1, 1, 1, 1]

    def test_fifth_wraps_to_next_row(self):
        assert button_row(4) == 2

    def test_twelfth_class_stays_within_row_limit(self):
        assert button_row(11) == 3

    def test_respects_custom_per_row_and_start_row(self):
        assert button_row(3, per_row=3, start_row=0) == 1


class TestExceedsMaxFutureOffset:
    def test_within_default_year_is_not_exceeded(self):
        assert exceeds_max_future_offset(0, 31536000) is False

    def test_just_over_default_year_is_exceeded(self):
        assert exceeds_max_future_offset(0, 31536001) is True

    def test_past_timestamp_is_not_exceeded(self):
        assert exceeds_max_future_offset(1000, 500) is False

    def test_respects_custom_max_offset(self):
        assert exceeds_max_future_offset(0, 3601, max_offset=3600) is True
        assert exceeds_max_future_offset(0, 3600, max_offset=3600) is False


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


class TestFormatPlayerEntry:
    CLASS_SPECS = [("<:Hunter:1>", "<:spec_red:9>"), ("<:Minstrel:2>", "")]

    def test_lists_class_and_spec_emojis(self):
        assert format_player_entry("Teri", self.CLASS_SPECS) == "Teri <:Hunter:1><:spec_red:9><:Minstrel:2>\n"

    def test_omits_spec_emojis_when_compact(self):
        assert format_player_entry("Teri", self.CLASS_SPECS, include_specs=False) == "Teri <:Hunter:1><:Minstrel:2>\n"

    def test_lineup_note_replaces_emojis(self):
        assert format_player_entry("Teri", self.CLASS_SPECS, lineup_note="(in line up)") == "Teri (in line up)\n"
