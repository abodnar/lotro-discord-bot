import builtins
import datetime
import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

from tests.raid_cog_harness import SOURCE, load_raid_cog

load_raid_cog()  # imports database with the harness config


def load_time_cog():
    spec = importlib.util.spec_from_file_location('time_cog_real', SOURCE / 'cogs' / 'time_cog.py')
    module = importlib.util.module_from_spec(spec)
    stubs = {name: MagicMock() for name in ('dateparser', 'pytz') if importlib.util.find_spec(name) is None}
    cwd = os.getcwd()
    os.chdir(SOURCE)  # the module reads data/common_timezones.txt on import
    try:
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(module)
    finally:
        os.chdir(cwd)
    return module


time_cog = load_time_cog()


class TestFormatWeekdayTime:
    def test_formats_weekday_and_time(self):
        assert time_cog.format_weekday_time(datetime.datetime(2026, 10, 2, 20, 5)) == 'Friday 20:05'

    def test_weekday_is_translated(self):
        # %A would follow the process locale; the weekday must go through gettext instead.
        french = {'Friday': 'vendredi'}
        with patch.object(builtins, '_', lambda s: french.get(s, s)):
            assert time_cog.format_weekday_time(datetime.datetime(2026, 10, 2, 20, 5)) == 'vendredi 20:05'


class TestNormalizeTimeInput:
    def test_military_time_gets_colon(self):
        assert time_cog.normalize_time_input('friday 2030') == 'friday 20:30'

    def test_bare_hour_with_h_becomes_clock_time(self):
        # dateparser reads "20h" as a 20-hour duration, or the 20th after a weekday.
        assert time_cog.normalize_time_input('vendredi 20h') == 'vendredi 20:00'
        assert time_cog.normalize_time_input('20h') == '20:00'
        assert time_cog.normalize_time_input('samedi 9h') == 'samedi 9:00'
        assert time_cog.normalize_time_input('viernes 20 h') == 'viernes 20:00'
        assert time_cog.normalize_time_input('Vendredi 20H') == 'Vendredi 20:00'

    def test_hour_with_minutes_left_alone(self):
        assert time_cog.normalize_time_input('vendredi 20h30') == 'vendredi 20h30'

    def test_duration_after_relative_word_left_alone(self):
        assert time_cog.normalize_time_input('dans 2h') == 'dans 2h'
        assert time_cog.normalize_time_input('in 2h') == 'in 2h'
        assert time_cog.normalize_time_input('en 3 h') == 'en 3 h'

    def test_words_and_out_of_range_hours_left_alone(self):
        assert time_cog.normalize_time_input('8pm') == '8pm'
        assert time_cog.normalize_time_input('tomorrow 8pm') == 'tomorrow 8pm'
        assert time_cog.normalize_time_input('25h') == '25h'
        assert time_cog.normalize_time_input('in 2 hours') == 'in 2 hours'
