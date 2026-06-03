from discord.ext import commands
import datetime
import discord
import logging
import psutil

from database import count, delete, select
from utils import chunks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DevCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = bot.conn

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, ext):
        ext = 'cogs.' + ext + '_cog'
        try:
            await self.bot.load_extension(ext)
            await ctx.send(_('Extension loaded.'))
        except commands.ExtensionAlreadyLoaded:
            await self.bot.reload_extension(ext)
            await ctx.send(_('Extension reloaded.'))
        except commands.ExtensionNotFound:
            await ctx.send(_('Extension not found.'))
        except commands.ExtensionError:
            await ctx.send(_('Extension failed to load.'))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def version(self, ctx, version):
        self.bot.version = version
        await self.bot.change_presence(activity=discord.Game(name=version))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def stats(self, ctx):
        guild_count = len(self.bot.guilds)
        member_count = sum([guild.member_count for guild in self.bot.guilds])

        available_memory = psutil.virtual_memory().available
        bot_process = psutil.Process()
        process_memory = bot_process.memory_info().vms
        cpu = bot_process.cpu_times()
        cpu_time = str(datetime.timedelta(seconds=cpu.system + cpu.user))

        def fmt_bytes(b):
            for unit in ('B', 'KB', 'MB', 'GB'):
                if b < 1024:
                    return f'{b:.1f} {unit}'
                b /= 1024
            return f'{b:.1f} GB'

        raid_count = count(self.conn, 'Raids', 'raid_id')
        player_count = count(self.conn, 'Players', 'player_id')
        slash_total = sum(
            (r[0] or 0)
            for r in select(self.conn, 'Settings', ['slash_count'])
        )

        about = [
            "**Resource usage:**",
            f"**CPU time:** {cpu_time}",
            f"**Memory:** {fmt_bytes(process_memory)} used / {fmt_bytes(available_memory)} free\n",
            f"**Servers:** {guild_count}",
            f"**Members:** {member_count}\n",
            f"**Active raids:** {raid_count}",
            f"**Players signed up:** {player_count}",
            f"**Slash commands used:** {slash_total}",
        ]
        embed = discord.Embed(title="Bot stats", colour=discord.Colour(0x3498db),
                              description="\n".join(about))
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def list(self, ctx):
        await ctx.send(_("**We are in the following {0} guilds:**\n").format(len(self.bot.guilds)))
        for chunk in chunks(self.bot.guilds, 40):
            msg = "\n".join("{0} ({1})".format(guild.name, guild.id) for guild in chunk)
            await ctx.send(msg)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def cleanup(self, ctx):
        res = select(self.conn, 'Settings', ['guild_id', 'last_command'])
        current_time = datetime.datetime.now().timestamp()
        cutoff_time = current_time - 3600 * 24 * 90
        active = inactive = deleted = 0
        for row in res:
            guild_id, last_command = row
            guild = self.bot.get_guild(guild_id)
            if guild:
                if last_command and last_command > cutoff_time:
                    active += 1
                else:
                    inactive += 1
                    logger.info("Leaving guild {0}...".format(guild.name))
                    await guild.leave()
            else:
                logger.info("We are no longer in {0}".format(guild_id))
                delete(self.conn, 'Settings', ['guild_id'], [guild_id])
                deleted += 1
        self.conn.commit()
        await ctx.send(f"Active: {active}  Inactive: {inactive}  Deleted: {deleted}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sync(self, ctx):
        await self.bot.tree.sync()
        logger.info("Synced bot commands.")
        await ctx.send("Synced bot commands.")


async def setup(bot):
    await bot.add_cog(DevCog(bot))
    logger.info("Loaded Dev Cog.")
