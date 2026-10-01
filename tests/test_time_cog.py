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
