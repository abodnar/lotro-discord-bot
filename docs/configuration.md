# Configuration

Configuration is split across two files:

| File | Contents | Committed? |
|------|----------|-----------|
| `source/config.json` | Secrets and instance settings | No (gitignored) |
| `source/game_data.json` | Classes, lineups, creeps | Yes |

---

## config.json

```json
{
  "BOT_TOKEN": "your-bot-token",
  "SERVER_TZ": "America/New_York",
  "LANGUAGE": "en"
}
```

| Key | Required | Description |
|-----|----------|-------------|
| `BOT_TOKEN` | Yes | Discord bot token |
| `SERVER_TZ` | Yes | Default timezone for raid times ([TZ database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |
| `LANGUAGE` | No | `en` (default) or `fr` |
| `HOST` | No | Guild ID whose custom emoji to use as fallback |

All values can also be set as environment variables (useful for Docker/CI).

---

## game_data.json

### CLASSES

Ordered list of playable class names. These must match the emoji names uploaded to Discord (or the application emoji names if using the default setup).

```json
"CLASSES": ["Beorning", "Brawler", "Burglar", "Captain", "Champion",
            "Guardian", "Hunter", "Loremaster", "Mariner", "Minstrel",
            "Runekeeper", "Warden"]
```

### DUOSPEC

Classes that only have two trait trees (Red and Blue — no Yellow). The `/specs` command will hide Yellow options for these.

```json
"DUOSPEC": ["Brawler", "Guardian", "Minstrel", "Warden"]
```

### CREEPS

Creep class names for Ettenmoors events (`/creep`).

```json
"CREEPS": ["Blackarrow", "Defiler", "Reaver", "Sorceress",
           "Stalker", "Warleader", "Weaver"]
```

### LINEUPS

Defines which classes are eligible for each roster slot, keyed by raid short name (the slash command name), raid size as a string, or `"default"`.

```json
"LINEUPS": {
  "default": [
    ["Minstrel", "Runekeeper"],
    ["Beorning", "Captain", "Minstrel", "Runekeeper"],
    ["Loremaster"],
    ["Burglar"],
    ["Brawler", "Captain", "Guardian"],
    ["Beorning", "Brawler", "Captain", "Guardian", "Warden"],
    ...
  ],
  "palace": [
    ["Minstrel", "Runekeeper"],
    ["Beorning", "Captain", "Minstrel", "Runekeeper"],
    ["Loremaster"],
    ["Burglar"],
    ["Brawler", "Captain", "Guardian"],
    ["Beorning", "Brawler", "Captain", "Guardian", "Warden"]
  ]
}
```

**Lookup order:** raid short name → raid size (e.g. `"6"`) → `"default"`.

Each sub-array is the list of classes that can fill that slot. The number of sub-arrays must be ≥ the raid's size in `list-of-raids.csv`; extra entries are ignored for smaller raids.

### Adding a new raid

Add a row to `source/data/list-of-raids.csv`:

```
shortname,Full Raid Name,size
```

Then optionally add a lineup entry keyed by `shortname` in `game_data.json`.
