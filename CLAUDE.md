# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
cd source
python3 main.py
```

All source files expect to be run from the `source/` directory (they open relative paths like `config.json`, `__init__.py`, `data/game_data.json`, `locale/`).

**Requirements:** Python >= 3.14

```bash
python3 -m pip install -U -r requirements.txt
```

**Docker:**
```bash
docker build -t lotro-bot . && docker run -e BOT_TOKEN=... -e SERVER_TZ=America/New_York lotro-bot
```

## Configuration

Copy `source/config.example.json` to `source/config.json` (running from source) or pass environment variables (Docker; the image excludes `config.json`):
- `BOT_TOKEN` — Discord bot token
- `SERVER_TZ` — TZ database name (e.g. `America/New_York`)
- `LANGUAGE` — `en`, `fr` or `es`; applies bot-wide (not per guild). Non-English needs a compiled `.mo` file

Game data lives in `source/data/game_data.json`:
- `CLASSES` — ordered list of class names
- `CREEPS` — optional creep class names for PvMP events
- `DUOSPEC` — optional list of classes that support dual specializations
- `DEFAULT_LINEUP` — one list of eligible class names per roster slot (a legacy `LINEUP` bitmask list is still accepted as a fallback)
- `RAIDS` — raid definitions keyed by short name: `name`, `size`, and an optional per-raid `lineup`

Config values can also be set as environment variables (fallback if not in `config.json`).

**Generating locale binary** (required for non-English): the Docker build compiles every `messages.po` into `messages.mo`. When running from source, compile `source/locale/<lang>/LC_MESSAGES/messages.po` into `messages.mo` in the same directory with `msgfmt`; `.mo` files are gitignored.

## Architecture

### Cog Loading Order (important)

`bot.py` loads cogs in a specific order with dependencies:
1. `config_cog` — guild settings (server TZ, raid leader role, kin role)
2. `dev_cog` — owner-only dev commands
3. `time_cog` — time parsing; must load before calendar_cog
4. `calendar_cog` — calendar channel management; must load before raid_cog
5. `raid_cog` — core raid scheduling; registers one slash command per entry in `RAIDS`
6. `rss_cog` — LotRO RSS feed posting
7. `treasure_cog` — loot lookup; always loads, graceful no-data state until !refreshlore is run
8. `custom_cog` — empty stub for local customization without merge conflicts

### Data Flow

- **SQLite database** (`raid_db`) persists all state: raids, player signups, assignments, timezones, guild settings, specs
- `database.py` provides a thin query-builder layer (`select`, `upsert`, `delete`, `increment`, `count`) — no ORM
- The `Players` table schema is dynamically generated from `CLASSES` + `CREEPS` config at startup; adding/removing classes requires a database migration
- Raid embed state is reconstructed from DB on bot restart via persistent `discord.ui.View` objects

### Raid Commands

Slash commands for individual raids are registered dynamically in `RaidCog.__init__` from `RAIDS` in `source/data/game_data.json`. Adding a new raid = adding an entry there (`"shortname": { "name": "Full Name", "size": 12 }`).

`DEFAULT_LINEUP` (or a raid's own `lineup`) controls which classes are eligible for each roster slot.

### Key Files

- `source/data/game_data.json` — classes, lineups, and raid definitions
- `source/__init__.py` — bot version (`__version__`)
- `data/lore/containers.xml`, `data/lore/loots.xml` — loot data for `/loot` command; auto-fetched from GitHub at startup if absent (see `source/lore_data.py`)
- `source/locale/` — i18n files; `messages.po` is source, `messages.mo` is compiled binary

### Internationalization

All user-facing strings use `_("string")` (GNU gettext). The `_` function is installed globally via `localization.install()` in `bot.py`. The `source/gen_locale_strings.sh` script (run from `source/`) extracts strings into `messages.pot` and merges them into the fr/es catalogs. Slash command names stay English on purpose: `/raid_help` looks commands up by their English names.
