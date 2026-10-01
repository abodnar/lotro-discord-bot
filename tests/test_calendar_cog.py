import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tests.raid_cog_harness import SOURCE, load_raid_cog, make_db

load_raid_cog()

from database import create_table, upsert  # noqa: E402  (needs the harness config)


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


def load_calendar_cog():
    discord = sys.modules['discord']
    discord.NotFound = NotFound
    discord.Forbidden = Forbidden
    spec = importlib.util.spec_from_file_location('calendar_cog_real', SOURCE / 'cogs' / 'calendar_cog.py')
    module = importlib.util.module_from_spec(spec)
    # Only the event helpers are tested; stub the time-parsing deps if they aren't installed.
    stubs = {name: MagicMock() for name in ('dateparser', 'pytz') if importlib.util.find_spec(name) is None}
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


calendar_cog = load_calendar_cog()

RAID_ID = 100
GUILD_ID = 1
EVENT_ID = 555


def make_cog(conn):
    cog = calendar_cog.CalendarCog.__new__(calendar_cog.CalendarCog)
    cog.bot = SimpleNamespace(conn=conn)
    cog.conn = conn
    return cog


def make_conn():
    conn = make_db()
    create_table(conn, 'settings')
    upsert(conn, 'Settings', ['guild_events'], [True], ['guild_id'], [GUILD_ID])
    upsert(conn, 'Raids', ['channel_id', 'guild_id', 'organizer_id', 'name', 'time', 'roster', 'tag', 'size', 'event_id'],
           [10, GUILD_ID, 5, 'Test Raid', 0, True, 'test1', 12, EVENT_ID], ['raid_id'], [RAID_ID])
    return conn


def missing_event_guild():
    return SimpleNamespace(id=GUILD_ID, fetch_scheduled_event=AsyncMock(side_effect=NotFound()))


class TestMissingGuildEvent:
    """A guild event deleted by hand in Discord must not abort raid edits or deletes."""

    async def test_delete_ignores_missing_event(self):
        guild = missing_event_guild()

        await make_cog(make_conn()).delete_guild_event(guild, RAID_ID)

        guild.fetch_scheduled_event.assert_awaited_once_with(EVENT_ID, with_counts=False)

    async def test_modify_ignores_missing_event(self):
        guild = missing_event_guild()

        await make_cog(make_conn()).modify_guild_event(guild, RAID_ID)

        guild.fetch_scheduled_event.assert_awaited_once_with(EVENT_ID, with_counts=False)
