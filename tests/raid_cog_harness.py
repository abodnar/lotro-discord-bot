"""Load the real cogs/raid_cog.py for tests.

conftest.py replaces discord and cogs.raid_cog with MagicMocks. Subclassing a
MagicMock yields another MagicMock, so the cog's classes would be unusable.
This installs minimal base classes on the mocked discord modules and imports
raid_cog from its file under a separate module name.
"""
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

SOURCE = Path(__file__).resolve().parent.parent / 'source'
CLASSES = ['Captain', 'Hunter', 'Guardian', 'Minstrel']


class _Item:
    def __init__(self, *args, **kwargs):
        self.view = None


class Select(_Item):
    values = []


class Button(_Item):
    pass


class View:
    def __init__(self, *args, **kwargs):
        self.children = []

    def add_item(self, item):
        item.view = self
        self.children.append(item)

    def stop(self):
        pass


class Modal(View):
    pass


class Cog:
    @staticmethod
    def listener(*args, **kwargs):
        return lambda func: func


# Real exception classes so `except discord.NotFound:` etc. work against the mocked module.
class HTTPException(Exception):
    pass


class Forbidden(HTTPException):
    pass


class NotFound(HTTPException):
    pass


class DiscordServerError(HTTPException):
    pass


def _install_discord_stubs():
    discord = sys.modules['discord']
    discord.ui.View = View
    discord.ui.Modal = Modal
    discord.ui.Select = Select
    discord.ui.Button = Button
    discord.HTTPException = HTTPException
    discord.Forbidden = Forbidden
    discord.NotFound = NotFound
    discord.DiscordServerError = DiscordServerError
    # `from discord.ext import commands` resolves the attribute, not sys.modules['discord.ext.commands']
    for commands in (sys.modules['discord.ext'].commands, sys.modules['discord.ext.commands']):
        commands.Cog = Cog


_module = None


def load_raid_cog():
    """Import the real raid_cog once, with CLASSES supplied via a temporary config.json."""
    global _module
    if _module is not None:
        return _module
    _install_discord_stubs()
    cwd = os.getcwd()
    real_time_cog = sys.modules.get('cogs.time_cog')
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, 'config.json').write_text(json.dumps({'CLASSES': CLASSES}))
        os.chdir(tmp)
        try:
            # time_cog needs dateparser/pytz; raid_cog only uses its Time converter in modals.
            # Swap only that entry: patch.dict would also drop `database`, which must stay imported
            # with this config.
            sys.modules['cogs.time_cog'] = MagicMock()
            spec = importlib.util.spec_from_file_location('raid_cog_real', SOURCE / 'cogs' / 'raid_cog.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            if real_time_cog is None:
                sys.modules.pop('cogs.time_cog', None)
            else:
                sys.modules['cogs.time_cog'] = real_time_cog
            os.chdir(cwd)
    _module = module
    return module


def make_db():
    """In-memory database with the raid tables, using the harness CLASSES."""
    load_raid_cog()  # imports database with the harness config
    import database
    conn = sqlite3.connect(':memory:')
    for table in ('raid', 'player', 'assign', 'specs'):
        database.create_table(conn, table)
    return conn
