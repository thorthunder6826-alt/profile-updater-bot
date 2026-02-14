# Gmail Link Telegram Bot

This repository includes a standalone Telegram bot in `main.py` that fetches links from your Gmail inbox.

## What it does

- `/fetchlink [subject keywords]`
  - Finds the latest email containing at least one URL
  - Prefers unseen emails first, then falls back to all emails
- `/fetchfrom <sender_email> [subject keywords]`
  - Same behavior, limited to a sender address
- `/checkgmail`
  - Confirms IMAP login and mailbox access

## Gmail setup (important)

For Gmail IMAP access, use an **App Password**:

1. Enable 2-Step Verification on your Google account.
2. Create an App Password (Mail app).
3. Use that 16-character app password as `GMAIL_APP_PASSWORD`.

## Environment variables

- `TELEGRAM_BOT_TOKEN` (required): Telegram bot token from BotFather
- `GMAIL_ADDRESS` (required): your Gmail address
- `GMAIL_APP_PASSWORD` (required): Gmail app password
- `ADMIN_USER_ID` (optional): only this Telegram user can use the bot
- `ALLOWED_USER_IDS` (optional): comma-separated user IDs allowed to use bot
- `GMAIL_IMAP_HOST` (optional): default `imap.gmail.com`
- `GMAIL_IMAP_PORT` (optional): default `993`
- `GMAIL_MAILBOX` (optional): default `INBOX`
- `FETCH_SCAN_LIMIT` (optional): number of newest emails to scan, default `30`

Access rules:

- If `ADMIN_USER_ID` is set, only that user is allowed unless additional users are included in `ALLOWED_USER_IDS`.
- If `ALLOWED_USER_IDS` is set without admin, only listed users are allowed.
- If neither is set, the bot is open to anyone who can message it.

## Run

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your_16_char_app_password"
export ADMIN_USER_ID="123456789"
python3 main.py
```

## Command examples

```text
/fetchlink
/fetchlink reset password
/fetchfrom no-reply@service.com verify
/checkgmail
```
