# Request-Driven Telegram Bot

This repository now includes a standalone Telegram bot in `main.py`.

## What it does

- Lets users submit request tickets with `/request <text>`
- Lets users check their own tickets with `/myrequests`
- Lets admin manage open tickets with:
  - `/openrequests`
  - `/close <ticket_id> [note]`
- Supports custom trigger-based replies:
  - `/set <trigger> | <response>`
  - `/delete <trigger>`
  - `/list`
  - Trigger by typing `/trigger` or plain text `trigger`

## Environment variables

- `TELEGRAM_BOT_TOKEN` (required): Telegram bot token from BotFather
- `ADMIN_USER_ID` (optional): Telegram user ID with admin rights
  - If omitted, all users can manage commands/tickets
- `BOT_DB_PATH` (optional): SQLite DB path (default: `telegram_bot.db`)

## Run

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export ADMIN_USER_ID="123456789"
python main.py
```

## Trigger format

Custom trigger names must be:

- lowercase letters
- digits and underscores allowed
- max 32 characters

Example:

```text
/set pricing | Pricing starts at $29/month.
```
