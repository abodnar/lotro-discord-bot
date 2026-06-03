import aiohttp
from datetime import datetime
import discord
from discord.ext import commands
from itertools import compress
import gettext
import json
import locale
import logging
import os
import re

from database import create_connection, create_table, increment, read_config_key, select, upsert
from emoji_manager import ensure_emojis


class Bot(commands.Bot):

    def __init__(self):
        self.launch_time = datetime.utcnow()

        version = ""
        with open('__init__.py') as f:
            regex = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
            version = re.search(regex, f.read(), re.MULTILINE).group(1)
        self.version = version

        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        self.logger = logger

        self.logger.info("Running version " + self.version)

        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            logger.warning("No config.json found. Please create it with BOT_TOKEN and SERVER_TZ.")
            config = {}

        try:
            with open('data/game_data.json', 'r') as f:
                game_data = json.load(f)
        except FileNotFoundError:
            logger.warning("No data/game_data.json found. Using config.json for game data (legacy).")
            game_data = config  # fall back to reading everything from config.json

        self.token = read_config_key(config, 'BOT_TOKEN', True)
        self.server_tz = read_config_key(config, 'SERVER_TZ', True)
        role_names = read_config_key(game_data, 'CLASSES', True)
        self.role_names = tuple(role_names)
        self.creep_names = read_config_key(game_data, 'CREEPS', False)
        # Lineups — prefer human-readable LINEUPS dict, fall back to bitmask LINEUP
        lineups_config = read_config_key(game_data, 'LINEUPS', False)
        if lineups_config:
            self.lineups = {key: slots for key, slots in lineups_config.items()}
        else:
            lineup = read_config_key(game_data, 'LINEUP', True)
            default_lineup = []
            for string in lineup:
                bitmask = [int(char) for char in string]
                default_lineup.append(bitmask)
            slots_class_names = []
            for bitmask in default_lineup:
                slots_class_names.append(list(compress(role_names, bitmask)))
            self.lineups = {'default': slots_class_names}
        self.slots_class_names = self.lineups.get('default', [])

        # Get id for discord server hosting custom emoji.
        host_id = read_config_key(config, 'HOST', False)
        if host_id:
            self.host_id = int(host_id)
        else:
            self.host_id = None

        language = read_config_key(config, 'LANGUAGE', False)
        if language == 'fr':
            locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
        localization = gettext.translation('messages', localedir='locale', languages=[language], fallback=True)
        if language == 'en' or hasattr(localization, '_catalog'):  # Technically 'en' has no file.
            logger.info("Using language file for '{0}'.".format(language))
        else:
            logger.warning("Language file '{0}' not found. Defaulting to English.".format(language))
        localization.install()

        conn = create_connection('raid_db')
        if conn:
            self.logger.info("Bot connected to raid database.")
            create_table(conn, 'settings')
        else:
            self.logger.error("main could not create database connection!")
        self.conn = conn

        intents = discord.Intents.none()
        intents.guilds = True
        intents.emojis = True
        intents.dm_messages = True

        super().__init__(command_prefix=self.prefix_manager, case_insensitive=True, intents=intents,
                         activity=discord.Game(name=self.version))

        async def globally_block_dms(ctx):
            if ctx.guild is None and not await ctx.bot.is_owner(ctx.author):
                raise commands.NoPrivateMessage("No dm allowed!")
            else:
                return True

        super().add_check(globally_block_dms)

    def prefix_manager(self, bot, message):
        return commands.when_mentioned_or("!")(bot, message)

    async def on_ready(self):
        self.logger.info("We have logged in as {0}.".format(self.user))
        if not self.guilds:
            self.logger.error("The bot is not in any guilds. Shutting down.")
            await self.close()
            return
        for guild in self.guilds:
            self.logger.info('Welcome to {0}, {1}.'.format(guild.name, guild.id))
        self.logger.info('We are in {0} guilds.'.format(len(self.guilds)))

        # Close old session if it already exists
        try:
            await self.http_session.close()
        except AttributeError:
            pass
        self.http_session = aiohttp.ClientSession()

        self.emojis_dict = await ensure_emojis(self, list(self.role_names), self.creep_names, 'emojis')
        self.logger.info(f'Application emojis ready: {len(self.emojis_dict)} loaded.')

        try:
            await self.load_extension('cogs.config_cog')
            await self.load_extension('cogs.dev_cog')
            await self.load_extension('cogs.time_cog')
            # Load after time cog
            await self.load_extension('cogs.calendar_cog')
            # Load after calendar_cog
            await self.load_extension('cogs.raid_cog')
            # Load rss cog
            await self.load_extension('cogs.rss_cog')
            # Load treasure cog (requires LotRO data submodule checked out)
            if os.path.exists('../data/lore/containers.xml'):
                await self.load_extension('cogs.treasure_cog')
            # Load custom cog
            await self.load_extension('cogs.custom_cog')
        except commands.ExtensionAlreadyLoaded:
            pass
        else:
            # Guild sync first (instant) while global tree is still populated
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            # Then clear global commands from Discord to prevent duplicates
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            self.logger.info("Synced slash commands.")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(_("You are not the bot owner."))
        else:
            if not isinstance(error, commands.CommandNotFound):
                self.logger.warning("Error for command: " + ctx.message.content)
                self.logger.warning(error)
            try:
                await ctx.send(error, delete_after=10)
            except discord.Forbidden:
                self.logger.warning("Missing Send messages permission for channel {0}".format(ctx.channel.id))

    async def on_app_command_error(self, interaction, error):
        self.logger.error(f"App command error in /{interaction.command}: {error}", exc_info=error)
        try:
            await interaction.response.send_message(str(error), ephemeral=True)
        except Exception:
            pass

    async def on_app_command_completion(self, interaction, command):
        timestamp = int(datetime.now().timestamp())
        guild_id = interaction.guild_id
        increment(self.conn, 'Settings', 'slash_count', ['guild_id'], [guild_id])
        res = upsert(self.conn, 'Settings', ['last_command'], [timestamp], ['guild_id'], [guild_id])
        if res:
            self.conn.commit()

    async def close(self):
        await self.http_session.close()
        await super().close()
