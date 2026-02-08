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
- Netflix selectors use multiple fallback patterns for robustness
- Browser lifecycle centralized via `_launch_browser()` and `_safe_close()` methods
- Profile data fetched via HTTP (httpx) for speed; browser automation only for mutations
- **CRITICAL: Never use `asyncio.wait_for()` around Playwright page operations** - it creates task cancellation pressure that disrupts Playwright's internal event loop, causing MFA dialogs to fail silently. Call `_do_set_pin()` directly instead.
- **CRITICAL: PIN setting MUST be sequential** - Netflix's MFA system is per-account, not per-profile. Running two MFA flows simultaneously causes one to fail (password dialog never appears). PINs run one-at-a-time with 0.5s delays between profiles, reusing a single browser instance for speed.
- **CRITICAL: Netflix rate-limits MFA** - Too many MFA attempts in rapid succession causes "something went wrong" error. The code detects this and uses exponential backoff on retries. Any failed PINs get an automatic retry pass after a 2s cooldown.
- **Email code MFA fallback**: When password MFA fails (rate-limited or "something went wrong"), the bot automatically falls back to email code verification: clicks "Email a code" → sends Telegram message asking user for the code → user replies with code → bot enters code and continues PIN flow. Uses `pending_email_codes` dict with `asyncio.Future` to bridge Telegram message handler with the browser automation flow. 5-minute timeout per code request.
- **Parallel processing**: Profile renames run in parallel (5 profiles in ~20s). PINs run sequentially (~7s per profile, ~35s for 5 profiles) using single browser reuse.
- **MFA handling**: PIN changes require password via MFA dialog - click "Edit PIN" → wait for dialog → "Confirm password" (force=True) → fill password → submit → fill PIN → save. Falls back to email code MFA if password confirmation fails. Entire flow retries up to 3 times with increasing backoff if MFA dialog fails.
- **Profile rename MFA**: Profile name edits on locked profiles trigger MFA without password option, so the bot uses a **delete+recreate fallback** (deletes old profile, creates new one with desired name) - recreates also run in parallel
- **Smart waiting**: Uses polling (250-300ms intervals) instead of fixed delays for faster operations

## Running
The `Start application` workflow runs `npm run dev` which starts both the Express server and the Python bot.
