import datetime
import discord
import logging
import __init__ as _meta

from discord import app_commands
from discord.ext import commands
from discord.utils import find

from database import upsert

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = self.bot.conn

    @staticmethod
    def td_format(td_object):
        seconds = int(td_object.total_seconds())
        periods = [
            ('year', 60 * 60 * 24 * 365),
            ('month', 60 * 60 * 24 * 30),
            ('day', 60 * 60 * 24),
            ('hour', 60 * 60),
            ('minute', 60),
            ('second', 1)
        ]

        strings = []
        for period_name, period_seconds in periods:
            if seconds > period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                has_s = 's' if period_value > 1 else ''
                strings.append("%s %s%s" % (period_value, period_name, has_s))

        return ", ".join(strings)

    _DEV = _meta.__author__
    _REPO = _meta.__repo__

    async def about_embed(self):
        dev = self._DEV
        repo = self._REPO
        app_info = await self.bot.application_info()
        try:
            host = app_info.team.name
        except AttributeError:
            host = app_info.owner.name
        uptime = datetime.datetime.utcnow() - self.bot.launch_time
        uptime = self.td_format(uptime)

        invite_link = "https://discord.com/api/oauth2/authorize?client_id={0}&permissions=8858388480&scope=bot" \
                      "%20applications.commands".format(self.bot.user.id)
        releases = repo + "/releases/latest"
        async with  self.bot.http_session.get(releases, allow_redirects=False) as r:
            if r.ok:
                try:
                    location = r.headers['location']
                except KeyError:
                    latest_version = "N/A"
                else:
                    (x, y, latest_version) = location.rpartition('/')
            else:
                latest_version = "N/A"

        title = "{0}".format(self.bot.user)
        about = [
            _("A bot for scheduling raids!"),
            _("**Developer:** {0}").format(dev),
            _("**[Source code]({0})**").format(repo),
            _("**[Invite me!]({0})**").format(invite_link),
            "",
            _("**Hosted by:** {0}").format(host),
            _("**Uptime:** {0}.").format(uptime),
            "",
            _("**Using version:** {0}").format(self.bot.version),
            _("**Latest version:** {0}").format(latest_version)
        ]

        content = "\n".join(about)
        embed = discord.Embed(title=title, colour=discord.Colour(0x3498db), description=content)
        return embed

    @staticmethod
    def welcome_msg(guild_name):
        msg = _("Greetings {0}! I am confined to Orthanc and here to spend my days doing your raid admin.\n\n"
                "You can quickly schedule a raid with the `/rem` and `/ad` commands. Examples:\n"
                "`/rem t2 Friday 8pm`\n"
                "`/ad t3 26 July 1pm`\n"
                "Use `/custom` to schedule a custom raid or meetup.\n\n"
                "With `/calendar` you can get an (automatically updated) overview of all scheduled raids. "
                "It is recommended you use a separate discord channel to display the calendar in.\n"
                "Use `/time_zones` to change the default time settings and "
                "you can designate a raid leader role with `/leader`, which allows non-admins to edit raids."
                ).format(guild_name)
        return msg

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        logger.info("We have joined {0}.".format(guild))
        timestamp = int(datetime.datetime.now().timestamp())
        upsert(self.conn, 'Settings', ['last_command'], [timestamp], ['guild_id'], [guild.id])
        self.conn.commit()
        # Sync commands to the new guild immediately
        self.bot.tree.copy_global_to(guild=guild)
        await self.bot.tree.sync(guild=guild)
        logger.info("Synced commands to {0}.".format(guild))
        channels = guild.text_channels
        channel = find(lambda x: x.name == 'welcome', channels)
        if not channel or not channel.permissions_for(guild.me).send_messages:
            channel = find(lambda x: x.name == 'general', channels)
        # Otherwise pick the first channel the bot can send a message in.
        if not channel or not channel.permissions_for(guild.me).send_messages:
            for ch in channels:
                if ch.permissions_for(guild.me).send_messages:
                    channel = ch
                    break
        if channel and channel.permissions_for(guild.me).send_messages:
            msg = self.welcome_msg(guild.name)
            await channel.send(msg)

    # Sections: maps section title → list of command names to include.
    # Names starting with * are shown as plain text (no slash command registered).
    _HELP_SECTIONS = [
        ("📅 Scheduling", [
            "*[raid name]",   # dynamic raid commands like /rem, /ad, /palace
            "custom", "creep",
        ]),
        ("✅ Sign-up", [
            "*class buttons",  # not a slash command
            "remove_roles", "specs",
        ]),
        ("📆 Calendar", [
            "calendar", "list_raids", "list_players",
        ]),
        ("ℹ️ Info", [
            "about", "events", "server_time", "loot",
        ]),
        ("⚙️ Server settings", [
            "leader", "kin", "time_zones", "rss",
        ]),
        ("👤 Personal settings", [
            "privacy",
        ]),
    ]

    # Descriptions for entries that aren't real slash commands
    _EXTRA_DESCRIPTIONS = {
        "*[raid name]": _("Schedule a specific raid — e.g. `/rem t3 friday 8pm`"),
        "*class buttons": _("Click a class icon on the raid post to sign up"),
    }

    async def _build_help_embed(self, guild: discord.Guild) -> discord.Embed:
        synced = await self.bot.tree.fetch_commands(guild=guild)
        cmd_map = {cmd.name: cmd for cmd in synced}

        embed = discord.Embed(title=_("LotRO Raid Bot — Commands"),
                              colour=discord.Colour(0x3498db))
        for section, names in self._HELP_SECTIONS:
            lines = []
            for name in names:
                if name.startswith("*"):
                    lines.append(self._EXTRA_DESCRIPTIONS[name])
                elif name in cmd_map:
                    cmd = cmd_map[name]
                    lines.append(f"</{cmd.name}:{cmd.id}> — {cmd.description}")
            if lines:
                embed.add_field(name=section, value="\n".join(lines), inline=False)
        return embed

    @app_commands.command(name=_("raid_commands"), description=_("Show all available raid bot commands."))
    @app_commands.guild_only()
    async def raid_commands_respond(self, interaction: discord.Interaction):
        embed = await self._build_help_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name=_("raid_help"), description=_("Show all available raid bot commands."))
    @app_commands.guild_only()
    async def raid_help_respond(self, interaction: discord.Interaction):
        embed = await self._build_help_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name=_("about"), description=_("Show information about this bot."))
    @app_commands.guild_only()
    async def about_respond(self, interaction: discord.Interaction):
        about = await self.about_embed()
        await interaction.response.send_message(embed=about)

    @app_commands.command(name=_("welcome"), description=_("Resend the welcome message."))
    @app_commands.guild_only()
    async def welcome_respond(self, interaction: discord.Interaction):
        welcome = self.welcome_msg(interaction.guild.name)
        await interaction.response.send_message(welcome)

    @app_commands.command(name=_("privacy"), description=_("Show information on data collection."))
    @app_commands.guild_only()
    async def privacy_respond(self, interaction: discord.Interaction):
        privacy = _("**Summary:**\n"
                     "When you sign up for a raid the bot stores the time, your discord id, discord nickname and the class("
                    "es) you sign up with. This information is automatically deleted 2 hours after the scheduled "
                    "raid time or immediately when you cancel your sign up.\n"
                    "If you set a default time zone for yourself, the bot will additionally store your time zone "
                    "along with your discord id such that it can parse times provided in your commands in your "
                    "preferred time zone.\n"
                    "**Please find the full privacy policy here:**\n"
                    f"{self._REPO}#privacy-policy")
        await interaction.response.send_message(privacy)


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
    logger.info("Loaded Config Cog.")
