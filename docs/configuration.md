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

### DEFAULT_LINEUP

The fallback slot configuration used for any raid without its own `lineup`. Each entry is the list of classes eligible for that slot.

```json
"DEFAULT_LINEUP": [
  ["Minstrel", "Runekeeper"],
  ["Beorning", "Captain", "Minstrel", "Runekeeper"],
  ["Loremaster"],
  ...
]
```

### RAIDS

All raid definitions in one place. Each key is the slash command name; `name` and `size` are required, `lineup` is optional and falls back to `DEFAULT_LINEUP` when absent.

```json
"RAIDS": {
  "rem":    { "name": "Remmorchant, the Net of Darkness", "size": 12 },
  "palace": {
    "name": "Ekal-nêbi, the Fallen Palace",
    "size": 6,
    "lineup": [
      ["Minstrel", "Runekeeper"],
      ["Beorning", "Captain", "Minstrel", "Runekeeper"],
      ["Loremaster"],
      ["Burglar"],
      ["Brawler", "Captain", "Guardian"],
      ["Beorning", "Brawler", "Captain", "Guardian", "Warden"]
    ]
  }
}
```

### Adding a new raid

Add an entry to `RAIDS` in `game_data.json`:

```json
"newraid": { "name": "Full Raid Name", "size": 12 }
```

Include a `lineup` array to override `DEFAULT_LINEUP` for that raid.
