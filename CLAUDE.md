# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
cd source
python3 main.py
```

All source files expect to be run from the `source/` directory (they open relative paths like `config.json`, `__init__.py`, `list-of-raids.csv`, `locale/`).

**Requirements:** Python >= 3.12

```bash
python3 -m pip install -U -r requirements.txt
```

**Docker:**
```bash
docker build -t lotro-bot . && docker run lotro-bot
```

## Configuration

Copy `source/example-config.json` to `source/config.json` and fill in:
- `BOT_TOKEN` — Discord bot token
- `CLASSES` — ordered list of class names (must match custom emoji names in your Discord server)
- `LINEUP` — bitmask strings (one per slot type), each character is 0/1 indicating whether that class fills that slot; length must match CLASSES length exactly
- `CREEPS` — optional creep class names for PvMP events
- `DUOSPEC` — optional list of classes that support dual specializations
- `SERVER_TZ` — TZ database name (e.g. `America/New_York`)
- `LANGUAGE` — `en` or `fr`; non-English requires generating a binary `.mo` file

Config values can also be set as environment variables (fallback if not in `config.json`).

**Generating locale binary** (required for non-English):
```bash
cd source/locale/<lang>/LC_MESSAGES
python3 ../../msgfmt.py messages.po
```

## Architecture

### Cog Loading Order (important)

`bot.py` loads cogs in a specific order with dependencies:
1. `config_cog` — guild settings (server TZ, raid leader role, kin role)
2. `dev_cog` — owner-only dev commands
3. `time_cog` — time parsing; must load before calendar_cog
4. `calendar_cog` — calendar channel management; must load before raid_cog
5. `raid_cog` — core raid scheduling; loads raid commands dynamically from `list-of-raids.csv`
6. `rss_cog` — LotRO RSS feed posting
7. `treasure_cog` — loot lookup; only loads if `../data/lore/containers.xml` exists
8. `custom_cog` — empty stub for local customization without merge conflicts

### Data Flow

- **SQLite database** (`raid_db`) persists all state: raids, player signups, assignments, timezones, guild settings, specs
- `database.py` provides a thin query-builder layer (`select`, `upsert`, `delete`, `increment`, `count`) — no ORM
- The `Players` table schema is dynamically generated from `CLASSES` + `CREEPS` config at startup; adding/removing classes requires a database migration
- Raid embed state is reconstructed from DB on bot restart via persistent `discord.ui.View` objects

### Raid Commands

Slash commands for individual raids are registered dynamically in `RaidCog.__init__` by reading `source/list-of-raids.csv` (format: `shortname,Full Name,size`). Adding a new raid = adding a row to that CSV.

The `LINEUP` config controls which class slots appear in which positions for the raid roster. Too many `1`s in any bitmask string will break the Discord embed UI.

### Key Files

- `source/list-of-raids.csv` — raid shortnames, full names, and sizes
- `source/__init__.py` — bot version (`__version__`) and LotRO data version (`__lotro__`)
- `data/lore/containers.xml`, `data/lore/loots.xml` — loot data for `/loot` command (not in repo by default)
- `source/locale/` — i18n files; `messages.po` is source, `messages.mo` is compiled binary

### Internationalization

All user-facing strings use `_("string")` (GNU gettext). The `_` function is installed globally via `localization.install()` in `bot.py`. The `source/gen_locale_strings.sh` script extracts strings for translation.
