import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
BOT_DB_PATH = os.environ.get("BOT_DB_PATH", "telegram_bot.db").strip()

TRIGGER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
BUILTIN_COMMANDS = {
    "start",
    "help",
    "set",
    "delete",
    "list",
    "request",
    "myrequests",
    "openrequests",
    "close",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("request-bot")


def now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(BOT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_commands (
                trigger TEXT PRIMARY KEY,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                request_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                admin_note TEXT,
                created_at TEXT NOT NULL,
                closed_at TEXT
            )
            """
        )


def can_manage(user_id: int) -> bool:
    # If ADMIN_USER_ID is not configured, every user can manage commands.
    return ADMIN_USER_ID == 0 or user_id == ADMIN_USER_ID


def get_custom_response(trigger: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT response FROM custom_commands WHERE trigger = ?",
            (trigger.lower(),),
        ).fetchone()
        return row["response"] if row else None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    management_note = (
        "You can manage commands with /set, /delete, /list.\n"
        if can_manage(user_id)
        else "Only admin can manage command templates.\n"
    )
    await update.message.reply_text(
        "Request Bot is live.\n\n"
        "Core commands:\n"
        "/request <text> - Create a request ticket\n"
        "/myrequests - Show your latest request tickets\n"
        "/help - Show command usage\n\n"
        + management_note
        + "\nType a saved trigger (or /trigger) to receive its configured reply."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    lines = [
        "How to use this bot:",
        "",
        "1) Save custom replies (admin):",
        "/set <trigger> | <response>",
        "Example: /set pricing | Pricing starts at $29/month.",
        "",
        "2) Use custom replies:",
        "Send: pricing",
        "or send: /pricing",
        "",
        "3) Track requests:",
        "/request <text>",
        "/myrequests",
    ]
    if can_manage(user_id):
        lines.extend(
            [
                "",
                "Admin request management:",
                "/openrequests",
                "/close <ticket_id> [note]",
                "/list",
                "/delete <trigger>",
            ]
        )
    await update.message.reply_text("\n".join(lines))


def parse_set_payload(text: str) -> tuple[Optional[str], Optional[str]]:
    if "|" not in text:
        return None, None
    left, right = text.split("|", 1)
    trigger = left.strip().lstrip("/").lower()
    response = right.strip()
    if not trigger or not response:
        return None, None
    return trigger, response


async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not can_manage(user_id):
        await update.message.reply_text("Only admin can use /set.")
        return

    raw_text = update.message.text or ""
    parts = raw_text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /set <trigger> | <response>")
        return

    trigger, response = parse_set_payload(parts[1])
    if not trigger or not response:
        await update.message.reply_text("Usage: /set <trigger> | <response>")
        return

    if trigger in BUILTIN_COMMANDS:
        await update.message.reply_text(
            f"'{trigger}' is reserved by a built-in bot command."
        )
        return

    if not TRIGGER_PATTERN.match(trigger):
        await update.message.reply_text(
            "Invalid trigger. Use lowercase letters, digits, underscores (max 32 chars)."
        )
        return

    timestamp = now_utc()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO custom_commands (trigger, response, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(trigger) DO UPDATE SET
                response = excluded.response,
                updated_at = excluded.updated_at
            """,
            (trigger, response, timestamp, timestamp),
        )

    await update.message.reply_text(f"Saved /{trigger}.")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not can_manage(user_id):
        await update.message.reply_text("Only admin can use /delete.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delete <trigger>")
        return

    trigger = context.args[0].lstrip("/").lower()
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM custom_commands WHERE trigger = ?",
            (trigger,),
        )

    if cursor.rowcount == 0:
        await update.message.reply_text(f"No custom command found for '{trigger}'.")
    else:
        await update.message.reply_text(f"Deleted /{trigger}.")


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT trigger, updated_at FROM custom_commands ORDER BY trigger ASC"
        ).fetchall()

    if not rows:
        await update.message.reply_text("No custom commands saved yet.")
        return

    lines = ["Saved custom commands:"]
    for row in rows:
        lines.append(f"- /{row['trigger']} (updated {row['updated_at']})")
    await update.message.reply_text("\n".join(lines))


async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    request_text = " ".join(context.args).strip()
    if not request_text:
        await update.message.reply_text("Usage: /request <text>")
        return

    user = update.effective_user
    username = user.username or user.full_name or ""
    timestamp = now_utc()

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO user_requests (user_id, username, request_text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user.id, username, request_text, timestamp),
        )
        ticket_id = cursor.lastrowid

    await update.message.reply_text(f"Request ticket #{ticket_id} created.")

    if ADMIN_USER_ID != 0 and user.id != ADMIN_USER_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    f"New request #{ticket_id}\n"
                    f"From: {username} ({user.id})\n"
                    f"Text: {request_text}"
                ),
            )
        except Exception as exc:
            logger.warning("Failed to forward request #%s to admin: %s", ticket_id, exc)


async def myrequests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, status, request_text, created_at, closed_at, admin_note
            FROM user_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text("You have no request tickets yet.")
        return

    lines = ["Your latest request tickets:"]
    for row in rows:
        line = f"#{row['id']} [{row['status']}] {row['request_text']}"
        if row["status"] == "closed":
            note = row["admin_note"] or "No note"
            line += f" | note: {note}"
        lines.append(line)
    await update.message.reply_text("\n".join(lines))


async def openrequests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not can_manage(update.effective_user.id):
        await update.message.reply_text("Only admin can use /openrequests.")
        return

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, username, request_text, created_at
            FROM user_requests
            WHERE status = 'open'
            ORDER BY id ASC
            LIMIT 20
            """
        ).fetchall()

    if not rows:
        await update.message.reply_text("No open request tickets.")
        return

    lines = ["Open request tickets:"]
    for row in rows:
        display_name = row["username"] or "unknown-user"
        lines.append(
            f"#{row['id']} from {display_name} ({row['user_id']}): {row['request_text']}"
        )
    await update.message.reply_text("\n".join(lines))


async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not can_manage(update.effective_user.id):
        await update.message.reply_text("Only admin can use /close.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /close <ticket_id> [note]")
        return

    try:
        ticket_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Ticket ID must be a number.")
        return

    note = " ".join(context.args[1:]).strip()
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE user_requests
            SET status = 'closed', closed_at = ?, admin_note = ?
            WHERE id = ? AND status = 'open'
            """,
            (now_utc(), note, ticket_id),
        )

    if cursor.rowcount == 0:
        await update.message.reply_text(
            f"No open ticket found with ID #{ticket_id}."
        )
    else:
        await update.message.reply_text(f"Closed ticket #{ticket_id}.")


async def custom_or_unknown_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    text = (update.message.text or "").strip()
    if not text.startswith("/"):
        return

    command_name = text[1:].split()[0].split("@")[0].lower()
    response = get_custom_response(command_name)
    if response:
        await update.message.reply_text(response)
        return

    await update.message.reply_text("Unknown command. Use /help.")


async def plain_text_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip().lower()
    if not text:
        return

    response = get_custom_response(text)
    if response:
        await update.message.reply_text(response)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN environment variable.")
        return

    if ADMIN_USER_ID == 0:
        logger.warning(
            "ADMIN_USER_ID is not set. All users can manage commands and tickets."
        )

    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("set", set_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("request", request_command))
    app.add_handler(CommandHandler("myrequests", myrequests_command))
    app.add_handler(CommandHandler("openrequests", openrequests_command))
    app.add_handler(CommandHandler("close", close_command))

    # Command lookup fallback so /custom_trigger works.
    app.add_handler(MessageHandler(filters.COMMAND, custom_or_unknown_command))
    # Plain-text lookup so typing "pricing" can also trigger reply.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_trigger))

    logger.info("Starting request-driven Telegram bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
