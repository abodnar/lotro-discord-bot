import asyncio
import discord
import logging
import xml.etree.ElementTree as ET

from discord import app_commands
from discord.ext import commands
from typing import Optional

import lore_data
from cogs.raid_cog import Classes
from utils import get_partial_matches

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

containerRoot = None
containers = {}
itemsTables = []
filteredTrophyTables = []
weightedTreasureTables = []
trophyLists = []
treasureLists = []
footer_text = _("Lore data not loaded yet.")


def load_lore_data():
    """Load and parse the lore XML files into module-level data structures.

    Parses into local variables first; the module globals below are only
    reassigned if both files parse successfully. Returns True on success,
    False if the files are missing or invalid (existing data, if any, is
    left untouched).
    """
    global containerRoot, containers, itemsTables, filteredTrophyTables
    global weightedTreasureTables, trophyLists, treasureLists, footer_text

    try:
        tree = ET.parse('../data/lore/containers.xml')
        new_containerRoot = tree.getroot()
        new_containers = {child.attrib['id']: child.attrib['name'] for child in new_containerRoot}
        tree = ET.parse('../data/lore/loots.xml')
        root = tree.getroot()
        new_itemsTables = root.findall("itemsTable")
        new_filteredTrophyTables = root.findall("filteredTrophyTable")
        new_weightedTreasureTables = root.findall("weightedTreasureTable")
        new_trophyLists = root.findall("trophyList")
        new_treasureLists = root.findall("treasureList")
    except (FileNotFoundError, ET.ParseError):
        return False

    info = lore_data.load_version_info()
    if 'version' in info:
        new_footer_text = _("Powered by LotroCompanion. Data as of U{0}").format(info['version'])
    elif 'fetched_date' in info:
        new_footer_text = _("Powered by LotroCompanion. Data fetched {0}").format(info['fetched_date'])
    else:
        new_footer_text = _("Powered by LotroCompanion.")

    containerRoot, containers = new_containerRoot, new_containers
    itemsTables, filteredTrophyTables = new_itemsTables, new_filteredTrophyTables
    weightedTreasureTables, trophyLists, treasureLists = new_weightedTreasureTables, new_trophyLists, new_treasureLists
    footer_text = new_footer_text
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
    for child in containerRoot:
        if child.attrib['id'] == containerID:
            try:
                filteredTrophyTableIDs.append(child.attrib['filteredTrophyTableId'])
                filteredTrophyTableIDs.append(child.attrib['filteredTrophyTableId2'])
                filteredTrophyTableIDs.append(child.attrib['filteredTrophyTableId3'])
            except KeyError:
                pass
            try:
                trophyListIDs.append([(1, child.attrib['trophyListId'])])
            except KeyError:
                pass
            try:
                trophyListIDs.append([(1, child.attrib['barterTrophyListId'])])
            except KeyError:
                pass
            try:
                treasureListIDs.append(child.attrib['treasureListId'])
            except KeyError:
                pass
            try:
                child.attrib['weightedTreasureTableId']
                #TODO
                raise NotImplementedError
            except KeyError:
                pass
            try:
                child.attrib['skirmishLootTableId']
                #TODO
                raise NotImplementedError
            except KeyError:
                pass
            return (filteredTrophyTableIDs, trophyListIDs, treasureListIDs)

def getTrophyListFromWeightedTreasureTable(weightedTreasureTableID, weightedTreasureTables):
    trophyListIDs = []
    for element in weightedTreasureTables:
        if element.attrib['id'] == weightedTreasureTableID:
            total = 0
            for entry in element:
                attributes = entry.attrib
                weight = int(attributes['weight'])
                total += weight
                trophyListID = attributes['trophyListId']
                trophyListIDs.append([weight, trophyListID])
            for trophyListID in trophyListIDs:
                trophyListID[0] = trophyListID[0]/total
            return trophyListIDs

def getTrophyListIDs(filteredTrophyTableIDs, trophyListIDs, _class, level):
    for filteredTrophyTableID in filteredTrophyTableIDs:
        for element in filteredTrophyTables:
            if element.attrib['id'] == filteredTrophyTableID:
                for entry in element:
                    try:
                        minLevel = int(entry.attrib['minLevel'])
                    except KeyError:
                        pass
                    else:
                        if minLevel > level:
                            continue
                    try:
                        maxLevel = int(entry.attrib['maxLevel'])
                    except KeyError:
                        pass
                    else:
                        if maxLevel < level:
                            continue
                    try:
                        requiredClass = entry.attrib['requiredClass']
                    except KeyError:
                        pass
                    else:
                        if _class not in requiredClass:
                            continue
                    try:
                        trophyListID = entry.attrib['trophyListId']
                        trophyListIDs.append([(1, trophyListID)])
                    except KeyError:
                        weightedTreasureTableID = entry.attrib['weightedTreasureTableId']
                        result = getTrophyListFromWeightedTreasureTable(weightedTreasureTableID, weightedTreasureTables)
                        trophyListIDs.append(result)
                        pass
                break
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
    for element in itemsTables:
        if element.attrib['id'] == treasureGroupProfileID:
            total = 0
            for entry in element:
                attributes = entry.attrib
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
    for element in treasureLists:
        if element.attrib['id'] == treasureGroupProfileID:
            for entry in element:
                result = getItemsFromTreasureGroup( entry.attrib['treasureGroupProfileId'], container_frequency)
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
            for element in trophyLists:
                if element.attrib['id'] == trophyListID[1]:
                    if weightedGroup:
                        assert(len(element) == 1)
                    for entry in element:
                        try:
                            treasureGroup = entry.attrib['treasureGroupProfileId']
                        except KeyError:
                            item = entry.attrib['name']
                            try:
                                quantity = entry.attrib['quantity'] + " "
                            except KeyError:
                                quantity = ""
                            if weightedGroup:
                                percentage = formatNumber(trophyListID[0] * 100)
                                item = ["{0}% -- {1}{2}".format(percentage, quantity, item)]
                            else:
                                item = ["100% -- " + quantity + item]
                        else:
                            item = getItemsFromTreasureGroup(treasureGroup, trophyListID[0])
                        frequency = float(entry.attrib['dropFrequency']) * 100
                        if weightedGroup:
                            assert(int(frequency) == 100)
                            loot[index][1].extend(item)
                        else:
                            loot.append([frequency, item])
                    break
    return loot

def appendTreasureDrops(treasureListIDs, loot):
    for treasureListID in treasureListIDs:
        for element in treasureLists:
            if element.attrib['id'] == treasureListID:
                for entry in element:
                    treasureGroup = entry.attrib['treasureGroupProfileId']
                    item = getItemsFromTreasureGroup(treasureGroup, 1)
                    #frequency = float(entry.attrib['dropFrequency']) * 100
                    loot.append([-1, item])
                break
    return loot

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
    if not current or containerRoot is None:
        return []
    suggestions = get_partial_matches(current, containers, keys=True)
    return [
        app_commands.Choice(name=containers[containerID], value=containerID)
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

    @app_commands.command(name=_("loot"), description=_("Shows drop chances for loot."))
    @app_commands.guild_only()
    @app_commands.describe(chest=_("The name of the container to see the drop table for."), classes=_("The class for which to see the drop table."), level=_("The character level for which to see the drop table."), tracery=_("Whether the tracery drop table should be shown in full."))
    @app_commands.autocomplete(chest=container_autocomplete)
    async def loot_respond(self, interaction: discord.Interaction, chest: str, classes: Optional[Classes]=Classes.Captain, level: Optional[app_commands.Range[int, 1, 160]]=160, tracery: Optional[bool]=False):
        if containerRoot is None:
            await interaction.response.send_message(_("Lore data not available. Ask the bot owner to run the refresh command."))
            return
        if chest not in containers.keys():
            await interaction.response.send_message(_("Unknown container."))
            return
        try:
            filteredTrophyTableIDs, trophyListIDs, treasureListIDs = getContainerContents(chest)
        except NotImplementedError:
            await interaction.response.send_message(_("Cannot parse obsolete container."))
            return
        if not tracery:
            traceryID = [_id for _id in filteredTrophyTableIDs if _id in traceryIDs]
            for _traceryID in traceryID:
                filteredTrophyTableIDs.remove(_traceryID)

        _class = classes.name
        queryClass = override_player_class(_class)
        trophyListIDs = getTrophyListIDs(filteredTrophyTableIDs, trophyListIDs, queryClass, level)
        loot = getItemDrops(trophyListIDs)
        if not tracery and traceryID and level>=50:
            if len(traceryID)==1:
                loot.append((100, [_("A tracery (pass tracery=True to expand this list)")]))
            else:
                loot.append((100, [_("{0} traceries (pass tracery=True to expand this list)").format(len(traceryID))]))
        loot = appendTreasureDrops(treasureListIDs, loot)
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
