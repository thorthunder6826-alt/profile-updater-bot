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

## Technical Notes
- Chromium launched with `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu` flags for Replit environment
- Per-task timeout: 60s for profile update, 90s for PIN set
- Netflix selectors use multiple fallback patterns for robustness
- Browser lifecycle centralized via `_launch_browser()` and `_safe_close()` methods
- Profile data fetched via HTTP (httpx) for speed; browser automation only for mutations
- **Sequential processing**: Both profile updates and PIN sets run sequentially (not parallel) to avoid Netflix MFA conflicts
- **MFA handling**: PIN changes accept password via MFA; profile name edits on locked profiles trigger MFA without password option, so the bot uses a **delete+recreate fallback** (deletes old profile, creates new one with desired name)
- **Smart waiting**: Uses polling (250-500ms intervals) instead of fixed delays for faster operations

## Running
The `Start application` workflow runs `npm run dev` which starts both the Express server and the Python bot.
