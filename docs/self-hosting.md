# Self-Hosting

## Prerequisites

- Docker
- A Discord application with a bot token ([create one here](https://discord.com/developers/applications))

## 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application
2. Under **Bot**, click **Reset Token** and copy it — this is your `BOT_TOKEN`
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**
4. Under **OAuth2 → URL Generator**, select scopes `bot` and `applications.commands`, permissions **Manage Roles**, **Send Messages**, **Embed Links**, **Manage Events**
5. Open the generated URL to invite the bot to your server

## 2. Configure

Create `source/config.json` with your secrets:

```json
{
  "BOT_TOKEN": "your-bot-token-here",
  "SERVER_TZ": "America/New_York",
  "LANGUAGE": "en"
}
```

Game data (classes, lineups) lives in `source/game_data.json` and is committed to the repo — see [Configuration](configuration.md) to customise it.

## 3. Run with Docker

```bash
docker build -t lotro-bot .
mkdir -p data
docker run -d --name lotro-bot \
  --restart unless-stopped \
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
  -e DB_PATH=/data/raid_db \
  -v $(pwd)/data:/data \
  lotro-bot
```

## Translations

The bot ships in English. To generate a binary for French or Spanish:

```bash
docker exec lotro-bot msgfmt locale/fr/LC_MESSAGES/messages.po -o locale/fr/LC_MESSAGES/messages.mo
```

Set `"LANGUAGE": "fr"` in `config.json` and rebuild.

To regenerate the translation template after code changes:

```bash
docker exec lotro-bot sh gen_locale_strings.sh
```
