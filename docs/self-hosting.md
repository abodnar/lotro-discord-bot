# Self-Hosting

## Prerequisites

- Docker
- A Discord application with a bot token ([create one here](https://discord.com/developers/applications))

## 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application
2. Under **Bot**, click **Reset Token** and copy it — this is your `BOT_TOKEN`
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**
4. Under **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`, permissions: **View Channels**, **Send Messages**, **Embed Links**, **Read Message History**, **Manage Roles**, **Manage Events**
   - Or use this permission integer: `8858455040`
   - Read Message History matters: the bot re-reads each raid post, and treats a post it can't read as deleted
5. Open the generated URL to invite the bot to your server

## 2. Configure

With Docker, settings are passed as environment variables:

| Variable | Example |
|----------|---------|
| `BOT_TOKEN` | your bot token |
| `SERVER_TZ` | `America/New_York` |
| `LANGUAGE` | `en`, `fr` or `es` (optional) |

`source/config.json` works too when running from source, but the Docker image doesn't include it.

Game data (classes, lineups, raids) lives in `source/data/game_data.json` and is committed to the repo — see [Configuration](configuration.md) to customise it.

## 3. Run with Docker

```bash
docker build -t lotro-bot .
mkdir -p data
docker run -d --name lotro-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=your-bot-token \
  -e SERVER_TZ=America/New_York \
  -e DB_PATH=/data/raid_db \
  -v $(pwd)/data:/data \
  lotro-bot
```

The database is persisted in `./data/` on the host.

To view logs:

```bash
docker logs -f lotro-bot
```

## 4. First Run

Slash commands sync to your server automatically on startup. Wait a few seconds then type `/` in Discord — all commands should appear.

## Updating

```bash
git pull
docker build -t lotro-bot .
docker stop lotro-bot && docker rm lotro-bot
docker run -d --name lotro-bot \
  --restart unless-stopped \
  -e BOT_TOKEN=your-bot-token \
  -e SERVER_TZ=America/New_York \
  -e DB_PATH=/data/raid_db \
  -v $(pwd)/data:/data \
  lotro-bot
```

## Translations

The bot speaks English, French or Spanish, set with `LANGUAGE` (`-e LANGUAGE=fr`). The language applies to every server the bot is in. The Docker build compiles the translations, so nothing else is needed. Slash command names stay in English.

After changing user-facing strings, regenerate the catalogs from `source/` (needs the gettext tools) and translate any new entries in `locale/<lang>/LC_MESSAGES/messages.po`:

```bash
cd source && sh gen_locale_strings.sh
```
