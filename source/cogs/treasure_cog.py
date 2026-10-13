import asyncio
import discord
import logging
import os
import sqlite3
import xml.etree.ElementTree as ET

from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from typing import Optional

import lore_data
import lore_db
from cogs.raid_cog import Classes
from utils import get_partial_matches

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

lore = None
containers = {}
containers_unique = {}
footer_text = _("Lore data not loaded yet.")


def _build_unique_containers(container_attrs, all_containers):
    """Return a subset of all_containers with duplicate loot tables removed.

    Two containers are considered duplicates if they share the same name and
    the same set of loot table reference IDs, meaning they drop identical loot.
    Only the first container ID encountered for each unique combination is kept.
    """
    seen = set()
    result = {}
    for attrs in container_attrs:
        cid = attrs['id']
        if cid not in all_containers:
            continue
        sig = (
            attrs.get('name', ''),
            attrs.get('filteredTrophyTableId', ''),
            attrs.get('filteredTrophyTableId2', ''),
            attrs.get('filteredTrophyTableId3', ''),
            attrs.get('trophyListId', ''),
            attrs.get('barterTrophyListId', ''),
            attrs.get('treasureListId', ''),
        )
        if sig not in seen:
            seen.add(sig)
            result[cid] = all_containers[cid]
    return result


def _db_is_stale(db_path, xml_paths):
    if not os.path.exists(db_path):
        return True
    db_mtime = os.path.getmtime(db_path)
    return any(os.path.exists(p) and os.path.getmtime(p) > db_mtime for p in xml_paths)


def load_lore_data():
    """Load the lore data, rebuilding the SQLite store if the XML is newer.

    The module globals below are only reassigned if the store builds and
    opens successfully. Returns True on success, False if the files are
    missing or invalid (existing data, if any, is left untouched).
    """
    global lore, containers, containers_unique, footer_text

    xml_paths = [os.path.join(lore_data.LORE_DIR, name) for name in lore_data.LORE_FILES]
    db_path = os.path.join(lore_data.LORE_DIR, 'lore.db')
    try:
        if _db_is_stale(db_path, xml_paths):
            lore_db.build(*xml_paths, db_path)
        new_lore = lore_db.LoreDB(db_path)
        container_attrs = new_lore.containers()
    except (OSError, ET.ParseError, sqlite3.Error):
        return False

    info = lore_data.load_version_info()
    if 'version' in info:
        new_footer_text = _("Powered by LotroCompanion. Data as of U{0}").format(info['version'])
    elif 'fetched_date' in info:
        new_footer_text = _("Powered by LotroCompanion. Data fetched {0}").format(info['fetched_date'])
    else:
        new_footer_text = _("Powered by LotroCompanion.")

    new_containers = {attrs['id']: attrs['name'] for attrs in container_attrs}
    old_lore, lore = lore, new_lore
    containers = new_containers
    containers_unique = _build_unique_containers(container_attrs, new_containers)
    footer_text = new_footer_text
    if old_lore is not None:
        old_lore.close()
    return True


if not load_lore_data():
    logger.warning("Lore data files not found at startup; /loot will be unavailable until !refreshlore is run.")

traceryIDs = ['1879428517', '1879428521', '1879428563', '1879428567']


#heavy = "Beorning;Captain;Champion;Guardian;Brawler"
#medium = "Burglar;Hunter;Corsair;Warden"
#light = "Lore-master;Minstrel;Rune-keeper"

def getContainerContents(containerID):
    filteredTrophyTableIDs = []
    trophyListIDs = []
    treasureListIDs = []
    attrs = lore.container(containerID)
    if attrs is not None:
        try:
            filteredTrophyTableIDs.append(attrs['filteredTrophyTableId'])
            filteredTrophyTableIDs.append(attrs['filteredTrophyTableId2'])
            filteredTrophyTableIDs.append(attrs['filteredTrophyTableId3'])
        except KeyError:
            pass
        try:
            trophyListIDs.append([(1, attrs['trophyListId'])])
        except KeyError:
            pass
        try:
            trophyListIDs.append([(1, attrs['barterTrophyListId'])])
        except KeyError:
            pass
        try:
            treasureListIDs.append(attrs['treasureListId'])
        except KeyError:
            pass
        try:
            attrs['weightedTreasureTableId']
            #TODO
            raise NotImplementedError
        except KeyError:
            pass
        try:
            attrs['skirmishLootTableId']
            #TODO
            raise NotImplementedError
        except KeyError:
            pass
        return (filteredTrophyTableIDs, trophyListIDs, treasureListIDs)

def getTrophyListFromWeightedTreasureTable(weightedTreasureTableID):
    trophyListIDs = []
    entries = lore.entries('weightedTreasureTable', weightedTreasureTableID)
    if entries is not None:
        total = 0
        for attributes in entries:
            weight = int(attributes['weight'])
            total += weight
            trophyListID = attributes['trophyListId']
            trophyListIDs.append([weight, trophyListID])
        for trophyListID in trophyListIDs:
            trophyListID[0] = trophyListID[0]/total
        return trophyListIDs

def getTrophyListIDs(filteredTrophyTableIDs, trophyListIDs, _class, level):
    for filteredTrophyTableID in filteredTrophyTableIDs:
        entries = lore.entries('filteredTrophyTable', filteredTrophyTableID)
        if entries is not None:
            for entry in entries:
                try:
                    minLevel = int(entry['minLevel'])
                except KeyError:
                    pass
                else:
                    if minLevel > level:
                        continue
                try:
                    maxLevel = int(entry['maxLevel'])
                except KeyError:
                    pass
                else:
                    if maxLevel < level:
                        continue
                try:
                    requiredClass = entry['requiredClass']
                except KeyError:
                    pass
                else:
                    if _class not in requiredClass:
                        continue
                try:
                    trophyListID = entry['trophyListId']
                    trophyListIDs.append([(1, trophyListID)])
                except KeyError:
                    weightedTreasureTableID = entry['weightedTreasureTableId']
                    result = getTrophyListFromWeightedTreasureTable(weightedTreasureTableID)
                    trophyListIDs.append(result)
    return trophyListIDs

def formatNumber(number):
    if number > 0.1:
        string = "%.2f" % number
    elif number > 0.01:
        string = "%.3f" % number
    else:
        string = "%.4f" % number
    return string

def getItemsFromTreasureGroup(treasureGroupProfileID, container_frequency):
    drops = []
    entries = lore.entries('itemsTable', treasureGroupProfileID)
    if entries is not None:
        total = 0
        for attributes in entries:
            weight = int(attributes['weight'])
            total += weight
            name = attributes['name']
            try:
                quantity = attributes['quantity'] + " "
            except KeyError:
                quantity = ""
            drops.append({'quantity': quantity, 'name': name, 'weight': weight})
        for drop in drops:
            percentage = drop['weight']/total * 100 * container_frequency
            drop['percentage'] = formatNumber(percentage)
        drops = sorted(drops, key=lambda d: -d['weight'])
        result = ["{0}% -- {1}{2}".format(drop['percentage'], drop['quantity'], drop['name']) for drop in drops]
        return result
    #For old chests treasureGroup can point to treasureList instead of itemList directly
    entries = lore.entries('treasureList', treasureGroupProfileID)
    if entries is not None:
        for entry in entries:
            result = getItemsFromTreasureGroup(entry['treasureGroupProfileId'], container_frequency)
            return(result)

def getItemDrops(trophyListIDs):
    loot = []
    for trophyListIDSet in trophyListIDs:
        if len(trophyListIDSet) > 1:
            weightedGroup = True
            index = len(loot)
            loot.append([100, []])
        else:
            weightedGroup = False
        for trophyListID in trophyListIDSet:
            entries = lore.entries('trophyList', trophyListID[1])
            if entries is not None:
                if weightedGroup:
                    assert(len(entries) == 1)
                for entry in entries:
                    try:
                        treasureGroup = entry['treasureGroupProfileId']
                    except KeyError:
                        item = entry['name']
                        try:
                            quantity = entry['quantity'] + " "
                        except KeyError:
                            quantity = ""
                        if weightedGroup:
                            percentage = formatNumber(trophyListID[0] * 100)
                            item = ["{0}% -- {1}{2}".format(percentage, quantity, item)]
                        else:
                            item = ["100% -- " + quantity + item]
                    else:
                        item = getItemsFromTreasureGroup(treasureGroup, trophyListID[0])
                    frequency = float(entry['dropFrequency']) * 100
                    if weightedGroup:
                        assert(int(frequency) == 100)
                        loot[index][1].extend(item)
                    else:
                        loot.append([frequency, item])
    return loot

def appendTreasureDrops(treasureListIDs, loot):
    for treasureListID in treasureListIDs:
        entries = lore.entries('treasureList', treasureListID)
        if entries is not None:
            for entry in entries:
                treasureGroup = entry['treasureGroupProfileId']
                item = getItemsFromTreasureGroup(treasureGroup, 1)
                #frequency = float(entry['dropFrequency']) * 100
                loot.append([-1, item])
    return loot

def _dedup_loot(loot):
    seen = set()
    result = []
    for freq, items in loot:
        key = (freq, tuple(items))
        if key not in seen:
            seen.add(key)
            result.append([freq, items])
    return result


def compute_loot(chest, _class, level, tracery):
    """Drop table for a container as [frequency, [item lines]] pairs; frequency -1 means unknown.

    Raises NotImplementedError for containers using loot tables we can't parse.
    """
    filteredTrophyTableIDs, trophyListIDs, treasureListIDs = getContainerContents(chest)
    traceryID = []
    if not tracery:
        traceryID = [_id for _id in filteredTrophyTableIDs if _id in traceryIDs]
        for _traceryID in traceryID:
            filteredTrophyTableIDs.remove(_traceryID)

    queryClass = override_player_class(_class)
    trophyListIDs = getTrophyListIDs(filteredTrophyTableIDs, trophyListIDs, queryClass, level)
    loot = getItemDrops(trophyListIDs)
    if not tracery and traceryID and level>=50:
        if len(traceryID)==1:
            loot.append((100, [_("A tracery (pass tracery=True to expand this list)")]))
        else:
            loot.append((100, [_("{0} traceries (pass tracery=True to expand this list)").format(len(traceryID))]))
    loot = appendTreasureDrops(treasureListIDs, loot)
    return _dedup_loot(loot)


def generateLootEmbed(loot, container, level, classes):
    title = _("Drop table for {0}").format(container)
    desc = _("Level {0} {1}").format(level, classes)
    embed = discord.Embed(title=title, description=desc, colour=discord.Colour(0x3498db))
    blocksize = 20
    for pair in loot:
        try:
            len(pair[1])
        except:
            logger.debug("Empty loot for {0}:\n{1}".format(container, loot))
            raise
        for i in range(0, len(pair[1]), blocksize):
            items = pair[1][i:i+blocksize]
            msg = "\n".join(items)
            if i == 0:
                if pair[0] == -1:
                    field_name = _("??% chance to get one of the following:")
                else:
                    field_name = _("%.3g%% chance to get one of the following:") % pair[0]
            else:
                field_name = "\u200b"
            embed.add_field(name=field_name, value=msg, inline=False)
    embed.set_footer(text=footer_text)
    return embed

async def container_autocomplete(interaction: discord.Interaction, current: str):
    if not current or lore is None:
        return []
    suggestions = get_partial_matches(current, containers_unique, keys=True)
    return [
        app_commands.Choice(name=containers_unique[containerID], value=containerID)
        for containerID in suggestions
    ]

def override_player_class(_class):
    match _class:
        case "Loremaster":
            return "Lore-master"
        case "Mariner":
            return "Corsair"
        case "Runekeeper":
            return "Rune-keeper"
        case _:
            return _class

class TreasureCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._refresh_lock = asyncio.Lock()

    async def cog_load(self):
        self.check_lore_updates.start()

    async def cog_unload(self):
        self.check_lore_updates.cancel()

    @tasks.loop(hours=24)
    async def check_lore_updates(self):
        async with self._refresh_lock:
            try:
                result = await lore_data.check_and_update_lore(self.bot.http_session)
            except Exception as e:
                logger.warning(f"Automatic lore update check failed: {e}")
                return
        if result is None:
            return
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, load_lore_data)
        if success:
            logger.info(f"Automatically updated lore data: {footer_text}")
        else:
            logger.warning("Automatically downloaded lore data failed to parse; keeping previous data.")

    @check_lore_updates.before_loop
    async def before_check_lore_updates(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name=_("loot"), description=_("Shows drop chances for loot."))
    @app_commands.guild_only()
    @app_commands.describe(chest=_("The name of the container to see the drop table for."), classes=_("The class for which to see the drop table."), level=_("The character level for which to see the drop table."), tracery=_("Whether the tracery drop table should be shown in full."))
    @app_commands.autocomplete(chest=container_autocomplete)
    async def loot_respond(self, interaction: discord.Interaction, chest: str, classes: Optional[Classes]=Classes.Captain, level: Optional[app_commands.Range[int, 1, 160]]=160, tracery: Optional[bool]=False):
        if lore is None:
            await interaction.response.send_message(_("Lore data not available. Ask the bot owner to run the refresh command."))
            return
        if chest not in containers.keys():
            await interaction.response.send_message(_("Unknown container."))
            return
        _class = classes.name
        try:
            loot = compute_loot(chest, _class, level, tracery)
        except NotImplementedError:
            await interaction.response.send_message(_("Cannot parse obsolete container."))
            return
        embed = generateLootEmbed(loot, containers[chest], level, _class)
        if len(embed) > 6000:
            # Check for send messages permission
            perms = interaction.channel.permissions_for(interaction.guild.me)
            if not (perms.send_messages and perms.embed_links):
                content = _("Missing permissions to send multiple messages in this channel.")
            else:
                content = _("Large container, responding with multiple embeds...")
            await interaction.response.send_message(content)
            drops = 0
            subloot = []
            for chunk in loot:
                # Roughly 200 drops fit in one embed, send and reset
                if drops + len(chunk[1]) > 200:
                    embed = generateLootEmbed(subloot, containers[chest], level, _class)
                    await interaction.channel.send(embed=embed)
                    drops = 0
                    subloot = []
                subloot.append(chunk)
                drops += len(chunk[1])
            embed = generateLootEmbed(subloot, containers[chest], level, _class)
            await interaction.channel.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def refreshlore(self, ctx):
        if self._refresh_lock.locked():
            await ctx.send(_("A lore data refresh is already in progress."))
            return
        async with self._refresh_lock:
            await ctx.send(_("Fetching latest lore data..."))
            try:
                await lore_data.fetch_lore_data(self.bot.http_session)
            except Exception as e:
                await ctx.send(_("Failed to fetch lore data: {0}").format(e))
                return
            loop = asyncio.get_running_loop()
            success = await loop.run_in_executor(None, load_lore_data)
            if success:
                await ctx.send(footer_text)
            else:
                await ctx.send(_("Downloaded data failed to parse; keeping previous data."))

async def setup(bot):
    await bot.add_cog(TreasureCog(bot))
    logger.info("Loaded Treasure Cog.")
