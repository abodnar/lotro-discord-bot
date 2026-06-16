import builtins
import sys
from enum import Enum
from unittest.mock import MagicMock

# Install gettext stub before any cog imports
builtins._ = lambda s: s

# Mock discord to avoid needing a live bot
for _mod in ['discord', 'discord.ext', 'discord.ext.commands', 'discord.ext.tasks', 'discord.app_commands']:
    sys.modules[_mod] = MagicMock()

# Mock cogs.raid_cog to avoid its module-level config/game_data.json reads
_mock_raid = MagicMock()
_mock_raid.Classes = Enum('Classes', ['Captain', 'Hunter', 'Guardian', 'Champion', 'Burglar'])
sys.modules['cogs.raid_cog'] = _mock_raid
