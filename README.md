# LotRO Raid Bot

A Discord bot for scheduling raids in Lord of the Rings Online. Players sign up via class buttons on the raid embed; raid leaders manage the roster, assign slots, and set per-slot spec and role requirements.

![Screenshot](./assets/screenshots/raid.png)

## Features

- **Raid scheduling** — post a raid with `/rem`, `/ad`, `/palace`, etc. with tier, time, and optional aim; `/custom` for anything else and `/creep` for Ettenmoors creep events
- **Natural-language times** — `friday 8pm`, `tomorrow 20:00`, read in each player's own time zone (`/time_zones personal`) or the server's
- **Class sign-up** — click class buttons to sign up; the embed updates in real time
- **Personal specs** — set your spec per class with `/specs`; it shows next to your name on sign-ups
- **Roster management** — raid leaders assign players to slots via the ⛏️ picker
- **Spec & role per slot** — mark each slot with a spec and role (🛡️ Tank, 💚 Healer, ⚡ CC, ⚔️ DPS)

  | Solid | Half | All three |
  |:-----:|:----:|:---------:|
  | <img src="assets/icons/spec_red.png" width="28"> <img src="assets/icons/spec_blue.png" width="28"> <img src="assets/icons/spec_yellow.png" width="28"> | <img src="assets/icons/spec_rb.png" width="28"> <img src="assets/icons/spec_by.png" width="28"> <img src="assets/icons/spec_ry.png" width="28"> | <img src="assets/icons/spec_all.png" width="28"> |
- **Per-instance lineups** — configure different slot compositions for different raids in `game_data.json`; `/lineup off` hides the suggested slots
- **Kin marking** — members of your kin role are marked on sign-ups with an emoji of your choice (`/kin`)
- **Application emoji** — class and spec icons work in any server without uploading custom emoji
- **Calendar** — auto-updating channel overview and Discord guild event integration
- **Raid notifications** — 5-minute warning pings assigned players before the raid starts
- **Auto-cleanup** — raid posts and data removed 2 hours after the scheduled time
- **Loot tables** — `/loot` shows drop chances for any chest, using LotroCompanion data fetched automatically
- **LotRO news** — official event schedule (`/events`) and forum announcements posted to a channel (`/rss on`)
- **Translations** — English, French and Spanish (`LANGUAGE`)

## Quick Start

See **[Self-Hosting](docs/self-hosting.md)** for full setup instructions.

**Requirements:** Docker

```bash
# 1. Clone the repo
git clone https://github.com/abodnar/lotro-discord-bot.git
cd lotro-discord-bot

# 2. Build and run (config comes from environment variables)
docker build -t lotro-bot .
mkdir -p data
docker run -d --name lotro-bot \
  -e BOT_TOKEN=your-bot-token \
  -e SERVER_TZ=America/New_York \
  -e DB_PATH=/data/raid_db \
  -v $(pwd)/data:/data \
  lotro-bot
```

## Documentation

- [Self-Hosting](docs/self-hosting.md) — Docker setup, Discord app configuration, first run
- [Configuration](docs/configuration.md) — `config.json` and `game_data.json` reference
- [Commands](docs/commands.md) — Full command reference

## Privacy

Use `/privacy` in Discord for data collection details, or `/raid_help` for a command overview.
