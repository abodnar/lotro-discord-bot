import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tests.raid_cog_harness import SOURCE, HTTPException, NotFound, load_raid_cog, make_db

load_raid_cog()

from database import create_table, upsert  # noqa: E402  (needs the harness config)


def load_calendar_cog():
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


def failing_event_guild(**event_errors):
    """A guild whose event exists but whose edit/delete calls raise the given errors."""
    event = SimpleNamespace(edit=AsyncMock(side_effect=event_errors.get('edit')),
                            delete=AsyncMock(side_effect=event_errors.get('delete')))
    return SimpleNamespace(id=GUILD_ID, fetch_scheduled_event=AsyncMock(return_value=event),
                           create_scheduled_event=AsyncMock(side_effect=event_errors.get('create'))), event


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


class TestGuildEventErrors:
    """Any Discord error on the event is logged; it must not abort the raid action."""

    async def test_modify_ignores_edit_error(self):
        # e.g. 400 when changing the start time of an event that has already started
        guild, event = failing_event_guild(edit=HTTPException())

        await make_cog(make_conn()).modify_guild_event(guild, RAID_ID)

        event.edit.assert_awaited_once()

    async def test_delete_ignores_delete_error(self):
        guild, event = failing_event_guild(delete=NotFound())

        await make_cog(make_conn()).delete_guild_event(guild, RAID_ID)

        event.delete.assert_awaited_once()

    async def test_create_returns_none_on_error(self):
        # e.g. 400 for a start time in the past
        guild, _ = failing_event_guild(create=HTTPException())

        assert await make_cog(make_conn()).create_guild_event(guild, RAID_ID) is None

    async def test_modify_ignores_deleted_raid(self):
        guild, event = failing_event_guild()
        conn = make_conn()
        conn.execute("delete from Raids where raid_id = ?", (RAID_ID,))

        await make_cog(conn).modify_guild_event(guild, RAID_ID)

        guild.fetch_scheduled_event.assert_not_awaited()
