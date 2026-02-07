# Netflix Profile Updater Bot

## Overview
A Telegram bot that automates Netflix profile management using Playwright browser automation. The bot runs as a Python process spawned by the Node.js/Express server.

## Architecture
- **Frontend**: React + Vite dashboard showing bot status and commands reference
- **Backend**: Express server (Node.js) that spawns a Python bot process
- **Bot**: Python script (`server/bot.py`) using `python-telegram-bot` and Playwright
- **Database**: PostgreSQL for authorized users table (managed by Python bot directly)

## Key Files
- `server/bot.py` - Full Python Telegram bot with Netflix automation
- `server/bot.ts` - Spawns the Python bot as a child process
- `server/routes.ts` - Express routes (bot status endpoint)
- `client/src/pages/Dashboard.tsx` - Status dashboard with commands reference

## Environment Variables
- `TELEGRAM_BOT_TOKEN` - Telegram bot API token (secret)
- `HOST_USER_ID` - Admin Telegram user ID (6401011033)
- `DATABASE_URL` - PostgreSQL connection string (auto-provisioned)

## Bot Commands
### Session
- `/login <cookie>` - Login with Netflix cookie
- `/loginemail <email> <password>` - Login with email/password
- `/profiles` - List all profiles
- `/logout` - Clear session

### Profile Management
- `/updateallprofiles <names...> <password>` - Update ALL profile names (parallel)
- `/updateallpins <pins...> <password>` - Set ALL PINs (parallel)
- `/addprofile <name>` - Add new profile
- `/deleteprofile <guid>` - Delete profile
- `/updateprofile <guid> <name>` - Update single profile
- `/setpin <guid> <pin> <password>` - Set single profile PIN

### Admin
- `/adduser <telegram_id>` - Authorize a user
- `/removeuser <telegram_id>` - Remove user authorization
- `/listusers` - List authorized users

## Running
The `Start application` workflow runs `npm run dev` which starts both the Express server and the Python bot.
