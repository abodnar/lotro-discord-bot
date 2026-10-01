from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tests.raid_cog_harness import Forbidden, NotFound, load_raid_cog, make_db

raid_cog = load_raid_cog()

from database import select_one, upsert  # noqa: E402  (needs the harness config)

RAID_ID = 100
GUILD_ID = 1
PLAYER_ID = 42
OLD_PLAYER_ID = 7


def add_raid(conn):
    upsert(conn, 'Raids', ['channel_id', 'guild_id', 'organizer_id', 'name', 'time', 'roster', 'tag', 'size'],
           [10, GUILD_ID, 5, 'Test Raid', 0, True, 'test1', 12], ['raid_id'], [RAID_ID])


class TestCleanupOldRaid:
    def make_cog(self, conn):
        cog = raid_cog.RaidCog.__new__(raid_cog.RaidCog)
        cog.conn = conn
        cog.bot = MagicMock()
        cog.calendar_cog = SimpleNamespace(update_calendar=AsyncMock())
        cog.raids = [RAID_ID]
        cog.update_call = {RAID_ID: 0}
        return cog

    async def test_deletes_existing_raid(self):
        conn = make_db()
        add_raid(conn)
        cog = self.make_cog(conn)
        cog.bot.get_guild.return_value = None

        await cog.cleanup_old_raid(RAID_ID, "test")

        assert select_one(conn, 'Raids', ['raid_id'], ['raid_id'], [RAID_ID]) is None
        assert RAID_ID not in cog.raids

    async def test_role_delete_failure_still_deletes_raid(self):
        # e.g. the raid role sits above the bot's role, or Manage Roles was revoked
        conn = make_db()
        add_raid(conn)
        cog = self.make_cog(conn)
        role = SimpleNamespace(delete=AsyncMock(side_effect=Forbidden()))

        with patch.object(raid_cog.discord.utils, 'get', return_value=role):
            await cog.cleanup_old_raid(RAID_ID, "test")

        role.delete.assert_awaited_once()
        assert select_one(conn, 'Raids', ['raid_id'], ['raid_id'], [RAID_ID]) is None
        assert RAID_ID not in cog.raids

    async def test_already_deleted_raid_is_ignored(self):
        cog = self.make_cog(make_db())

        await cog.cleanup_old_raid(RAID_ID, "test")

        assert RAID_ID not in cog.raids
        assert RAID_ID not in cog.update_call


class TestClassSelectCallback:
    """ClassSelect must answer the interaction before slower member/role API calls,
    or Discord expires the interaction after 3 seconds (404 Unknown interaction)."""

    def make_select(self, conn, value):
        cog = SimpleNamespace(role_names=['Captain', 'Hunter', 'Guardian', 'Minstrel'], emojis_dict={},
                              slots_class_names={0: ['Hunter'], 1: ['Guardian']},
                              update_raid_post=AsyncMock())
        select = raid_cog.ClassSelect(cog)
        select.view = SimpleNamespace(raid_id=RAID_ID, player=PLAYER_ID, slot=0, conn=conn, raid_cog=cog)
        select.values = [value]
        return select

    def make_interaction(self):
        calls = []

        def record(name, result=None):
            async def call(*args, **kwargs):
                calls.append(name)
                return result
            return call

        member = SimpleNamespace(add_roles=record('add_roles'), remove_roles=record('remove_roles'))
        interaction = SimpleNamespace(
            response=SimpleNamespace(send_message=record('send_message')),
            guild=SimpleNamespace(roles=[], fetch_member=record('fetch_member', member)),
            channel=MagicMock(),
        )
        return interaction, calls

    def setup_db(self):
        conn = make_db()
        add_raid(conn)
        upsert(conn, 'Players', ['byname', 'Hunter', 'unavailable'], ['Teri', True, False],
               ['raid_id', 'player_id'], [RAID_ID, PLAYER_ID])
        return conn

    async def test_assign_responds_before_member_calls(self):
        conn = self.setup_db()
        # Slot 0 is held by another player whose role must be removed.
        upsert(conn, 'Assignment', ['player_id', 'byname', 'class_name'], [OLD_PLAYER_ID, 'Old', 'Hunter'],
               ['raid_id', 'slot_id'], [RAID_ID, 0])
        select = self.make_select(conn, 'Hunter')
        interaction, calls = self.make_interaction()

        await select.callback(interaction)

        assert calls[0] == 'send_message'
        assert calls.count('fetch_member') == 2
        assert select_one(conn, 'Assignment', ['player_id'], ['raid_id', 'slot_id'], [RAID_ID, 0]) == PLAYER_ID

    async def test_remove_responds_before_member_calls(self):
        conn = self.setup_db()
        upsert(conn, 'Assignment', ['player_id', 'byname', 'class_name'], [PLAYER_ID, 'Teri', 'Hunter'],
               ['raid_id', 'slot_id'], [RAID_ID, 0])
        select = self.make_select(conn, 'remove')
        interaction, calls = self.make_interaction()

        await select.callback(interaction)

        assert calls[0] == 'send_message'
        assert 'remove_roles' in calls
        assert select_one(conn, 'Assignment', ['player_id'], ['raid_id', 'slot_id'], [RAID_ID, 0]) is None


class TestSignUpCancel:
    async def test_assigned_player_cancel_pings_organiser(self):
        conn = make_db()
        add_raid(conn)  # organizer_id 5
        upsert(conn, 'Players', ['byname', 'Hunter', 'unavailable'], ['Teri', True, False],
               ['raid_id', 'player_id'], [RAID_ID, PLAYER_ID])
        upsert(conn, 'Assignment', ['player_id', 'byname', 'class_name'], [PLAYER_ID, 'Teri', 'Hunter'],
               ['raid_id', 'slot_id'], [RAID_ID, 0])
        view = raid_cog.RaidView.__new__(raid_cog.RaidView)
        view.conn = conn
        view.raid_cog = SimpleNamespace(slots_class_names={0: ['Hunter']}, update_raid_post=AsyncMock(),
                                        process_name=MagicMock(return_value='Teri'))
        interaction = SimpleNamespace(
            response=SimpleNamespace(defer=AsyncMock()),
            message=SimpleNamespace(id=RAID_ID),
            user=SimpleNamespace(id=PLAYER_ID, mention=f'<@{PLAYER_ID}>', remove_roles=AsyncMock()),
            guild=SimpleNamespace(id=GUILD_ID, roles=[]),
            channel=SimpleNamespace(send=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

        await view.sign_up_cancel(interaction)

        sent = interaction.channel.send.await_args.args[0]
        assert sent.startswith('<@5>,')
        assert f'<@{PLAYER_ID}>' in sent


class TestCheckRaids:
    NOW = 10_000  # add_raid schedules at time 0, so the raid has expired by now

    def make_cog(self, conn, channel):
        cog = TestCleanupOldRaid().make_cog(conn)
        cog.bot.get_channel.return_value = channel
        cog.bot.get_guild.return_value = None
        return cog

    def make_channel(self, post):
        return SimpleNamespace(id=10, fetch_message=AsyncMock(return_value=post), send=AsyncMock())

    async def test_missing_channel_cleans_up_raid(self):
        conn = make_db()
        add_raid(conn)
        cog = self.make_cog(conn, None)

        await cog.check_raids(self.NOW)

        assert select_one(conn, 'Raids', ['raid_id'], ['raid_id'], [RAID_ID]) is None

    async def test_expired_raid_is_deleted(self):
        conn = make_db()
        add_raid(conn)
        post = SimpleNamespace(delete=AsyncMock())
        cog = self.make_cog(conn, self.make_channel(post))

        await cog.check_raids(self.NOW)

        post.delete.assert_awaited_once()
        assert select_one(conn, 'Raids', ['raid_id'], ['raid_id'], [RAID_ID]) is None

    async def test_expired_post_already_gone_is_ignored(self):
        # The post can be deleted by someone else between fetch_message and delete.
        conn = make_db()
        add_raid(conn)
        post = SimpleNamespace(delete=AsyncMock(side_effect=NotFound()))
        cog = self.make_cog(conn, self.make_channel(post))

        await cog.check_raids(self.NOW)

        post.delete.assert_awaited_once()
        assert select_one(conn, 'Raids', ['raid_id'], ['raid_id'], [RAID_ID]) is None

    async def test_upcoming_raid_notifies_channel(self):
        conn = make_db()
        add_raid(conn)
        channel = self.make_channel(SimpleNamespace(delete=AsyncMock()))
        cog = self.make_cog(conn, channel)

        await cog.check_raids(-100)  # raid starts in 100 seconds

        channel.send.assert_awaited_once()
        assert '<@5>' in channel.send.await_args.args[0]  # no assignments, so the organiser is pinged
