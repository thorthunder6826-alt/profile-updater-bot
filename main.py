import asyncio
import email
import html
import imaplib
import logging
import os
import re
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from email.policy import default as default_policy
from typing import Iterable, Optional, Sequence

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
GMAIL_IMAP_HOST = os.environ.get("GMAIL_IMAP_HOST", "imap.gmail.com").strip()
GMAIL_IMAP_PORT = int(os.environ.get("GMAIL_IMAP_PORT", "993"))
GMAIL_MAILBOX = os.environ.get("GMAIL_MAILBOX", "INBOX").strip()
FETCH_SCAN_LIMIT = max(1, int(os.environ.get("FETCH_SCAN_LIMIT", "30")))
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))

ALLOWED_USER_IDS_RAW = os.environ.get("ALLOWED_USER_IDS", "")

URL_PATTERN = re.compile(r"https?://[^\s<>'\"`]+", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gmail-link-bot")


def parse_allowed_user_ids(raw_value: str) -> set[int]:
    allowed: set[int] = set()
    for token in raw_value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            allowed.add(int(token))
        except ValueError:
            logger.warning("Skipping invalid ALLOWED_USER_IDS entry: %s", token)
    return allowed


ALLOWED_USER_IDS = parse_allowed_user_ids(ALLOWED_USER_IDS_RAW)


def is_authorized(user_id: int) -> bool:
    if ADMIN_USER_ID != 0 and user_id == ADMIN_USER_ID:
        return True
    if ALLOWED_USER_IDS:
        return user_id in ALLOWED_USER_IDS
    if ADMIN_USER_ID != 0:
        return False
    return True


async def ensure_authorized(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if is_authorized(user.id):
        return True
    if update.message:
        await update.message.reply_text("You are not authorized to use this bot.")
    return False


def decode_header_value(value: Optional[str]) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(encoding or "utf-8", errors="replace"))
            except LookupError:
                parts.append(part.decode("utf-8", errors="replace"))
        else:
            parts.append(part)
    return "".join(parts).strip()


def decode_part_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return raw_payload if isinstance(raw_payload, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def extract_text_bodies(message: Message) -> list[str]:
    bodies: list[str] = []
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            if content_type in {"text/plain", "text/html"}:
                text = decode_part_payload(part)
                if text:
                    bodies.append(text)
    else:
        content_type = message.get_content_type()
        if content_type in {"text/plain", "text/html"}:
            text = decode_part_payload(message)
            if text:
                bodies.append(text)
    return bodies


def normalize_url(candidate: str) -> str:
    # Email HTML frequently wraps URLs with trailing punctuation.
    url = html.unescape(candidate.strip())
    while url and url[-1] in ".,);:!?]>\"'":
        url = url[:-1]
    while url and url[0] in "(<\"'":
        url = url[1:]
    return url


def unique_links(links: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in links:
        normalized = normalize_url(item)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def select_best_link(links: Sequence[str]) -> Optional[str]:
    if not links:
        return None
    high_priority_words = ("verify", "reset", "confirm", "activate", "magic", "login")
    for link in links:
        lowered = link.lower()
        if any(word in lowered for word in high_priority_words):
            return link

    low_priority_words = ("unsubscribe", "viewinbrowser", "email-preferences")
    for link in links:
        lowered = link.lower()
        if not any(word in lowered for word in low_priority_words):
            return link
    return links[0]


def extract_links_from_message(message: Message) -> list[str]:
    bodies = extract_text_bodies(message)
    raw_links: list[str] = []
    for body in bodies:
        raw_links.extend(URL_PATTERN.findall(body))
    return unique_links(raw_links)


@dataclass
class LinkResult:
    link: str
    subject: str
    from_header: str
    seen: bool


class GmailLinkFetcher:
    def __init__(
        self,
        gmail_address: str,
        app_password: str,
        host: str,
        port: int,
        mailbox: str,
        scan_limit: int,
    ):
        self.gmail_address = gmail_address
        self.app_password = app_password
        self.host = host
        self.port = port
        self.mailbox = mailbox
        self.scan_limit = scan_limit

    def _connect(self) -> imaplib.IMAP4_SSL:
        client = imaplib.IMAP4_SSL(self.host, self.port, timeout=20)
        client.login(self.gmail_address, self.app_password)
        status, _ = client.select(self.mailbox)
        if status != "OK":
            raise RuntimeError(f"Could not open mailbox '{self.mailbox}'")
        return client

    @staticmethod
    def _build_search_criteria(unseen_only: bool, sender: Optional[str]) -> list[str]:
        criteria: list[str] = ["UNSEEN" if unseen_only else "ALL"]
        if sender:
            criteria.extend(["FROM", f'"{sender}"'])
        return criteria

    @staticmethod
    def _decode_message(raw_data: bytes) -> Message:
        return email.message_from_bytes(raw_data, policy=default_policy)

    @staticmethod
    def _subject_matches(subject: str, subject_filter: Optional[str]) -> bool:
        if not subject_filter:
            return True
        return subject_filter.lower() in subject.lower()

    def _search(self, client: imaplib.IMAP4_SSL, criteria: list[str]) -> list[bytes]:
        status, data = client.search(None, *criteria)
        if status != "OK" or not data:
            return []
        if not data[0]:
            return []
        ids = data[0].split()
        if not ids:
            return []
        return ids[-self.scan_limit :]

    def _fetch_email_message(
        self, client: imaplib.IMAP4_SSL, msg_id: bytes
    ) -> Optional[Message]:
        status, data = client.fetch(msg_id, "(RFC822)")
        if status != "OK" or not data:
            return None
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                payload = item[1]
                if isinstance(payload, bytes):
                    return self._decode_message(payload)
        return None

    def find_latest_link(
        self,
        sender: Optional[str] = None,
        subject_filter: Optional[str] = None,
    ) -> Optional[LinkResult]:
        client: Optional[imaplib.IMAP4_SSL] = None
        try:
            client = self._connect()

            # Prefer unseen emails first; if not found, fall back to all messages.
            phases = [True, False]
            for unseen_only in phases:
                criteria = self._build_search_criteria(unseen_only, sender)
                message_ids = self._search(client, criteria)
                for message_id in reversed(message_ids):
                    msg = self._fetch_email_message(client, message_id)
                    if msg is None:
                        continue
                    subject = decode_header_value(msg.get("Subject"))
                    from_header = decode_header_value(msg.get("From"))

                    if not self._subject_matches(subject, subject_filter):
                        continue

                    links = extract_links_from_message(msg)
                    best_link = select_best_link(links)
                    if best_link:
                        return LinkResult(
                            link=best_link,
                            subject=subject or "(no subject)",
                            from_header=from_header or "(unknown sender)",
                            seen=not unseen_only,
                        )
            return None
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
                try:
                    client.logout()
                except Exception:
                    pass

    def check_connection(self) -> tuple[bool, str]:
        client: Optional[imaplib.IMAP4_SSL] = None
        try:
            client = self._connect()
            status, data = client.search(None, "ALL")
            if status != "OK":
                return False, "Connected but mailbox search failed."
            total = len(data[0].split()) if data and data[0] else 0
            return True, f"Gmail connected. Mailbox '{self.mailbox}' has {total} emails."
        except imaplib.IMAP4.error as exc:
            return False, f"Gmail auth failed: {exc}"
        except Exception as exc:
            return False, f"Gmail connection error: {exc}"
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
                try:
                    client.logout()
                except Exception:
                    pass


FETCHER = GmailLinkFetcher(
    gmail_address=GMAIL_ADDRESS,
    app_password=GMAIL_APP_PASSWORD,
    host=GMAIL_IMAP_HOST,
    port=GMAIL_IMAP_PORT,
    mailbox=GMAIL_MAILBOX,
    scan_limit=FETCH_SCAN_LIMIT,
)


def parse_fetchfrom_args(args: list[str]) -> tuple[Optional[str], Optional[str]]:
    if not args:
        return None, None
    sender = args[0].strip()
    subject_filter = " ".join(args[1:]).strip() or None
    return sender or None, subject_filter


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update):
        return
    await update.message.reply_text(
        "Gmail Link Bot is ready.\n\n"
        "Commands:\n"
        "/fetchlink [subject keywords] - fetch latest link from your Gmail\n"
        "/fetchfrom <sender_email> [subject keywords] - fetch latest link from sender\n"
        "/checkgmail - verify Gmail connection\n"
        "/help - show usage"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update):
        return
    await update.message.reply_text(
        "Usage examples:\n\n"
        "1) Get latest link (prefer unseen emails):\n"
        "/fetchlink\n\n"
        "2) Get latest link with subject filter:\n"
        "/fetchlink reset password\n\n"
        "3) Get latest link from specific sender:\n"
        "/fetchfrom no-reply@example.com verify\n\n"
        "Setup required env vars:\n"
        "TELEGRAM_BOT_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD"
    )


async def checkgmail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update):
        return
    status_message = await update.message.reply_text("Checking Gmail connection...")
    ok, info = await asyncio.to_thread(FETCHER.check_connection)
    await status_message.edit_text(("OK: " if ok else "FAIL: ") + info)


async def fetchlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update):
        return

    subject_filter = " ".join(context.args).strip() or None
    wait_message = await update.message.reply_text("Looking for the latest link...")

    try:
        result = await asyncio.to_thread(
            FETCHER.find_latest_link, None, subject_filter
        )
    except imaplib.IMAP4.error as exc:
        await wait_message.edit_text(f"Gmail auth error: {exc}")
        return
    except Exception as exc:
        await wait_message.edit_text(f"Gmail fetch error: {exc}")
        return

    if not result:
        await wait_message.edit_text(
            "No email with a link was found for the current filters."
        )
        return

    seen_text = "seen" if result.seen else "unseen"
    await wait_message.edit_text(
        "Latest link found:\n"
        f"{result.link}\n\n"
        f"From: {result.from_header}\n"
        f"Subject: {result.subject}\n"
        f"Source: {seen_text} email"
    )


async def fetchfrom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_authorized(update):
        return

    sender, subject_filter = parse_fetchfrom_args(context.args)
    if not sender:
        await update.message.reply_text(
            "Usage: /fetchfrom <sender_email> [subject keywords]"
        )
        return

    wait_message = await update.message.reply_text(
        f"Looking for latest link from {sender}..."
    )

    try:
        result = await asyncio.to_thread(
            FETCHER.find_latest_link,
            sender,
            subject_filter,
        )
    except imaplib.IMAP4.error as exc:
        await wait_message.edit_text(f"Gmail auth error: {exc}")
        return
    except Exception as exc:
        await wait_message.edit_text(f"Gmail fetch error: {exc}")
        return

    if not result:
        await wait_message.edit_text(
            "No link found from that sender with the current filters."
        )
        return

    seen_text = "seen" if result.seen else "unseen"
    await wait_message.edit_text(
        "Latest link found:\n"
        f"{result.link}\n\n"
        f"From: {result.from_header}\n"
        f"Subject: {result.subject}\n"
        f"Source: {seen_text} email"
    )


def validate_configuration() -> list[str]:
    errors: list[str] = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("Missing TELEGRAM_BOT_TOKEN")
    if not GMAIL_ADDRESS:
        errors.append("Missing GMAIL_ADDRESS")
    if not GMAIL_APP_PASSWORD:
        errors.append("Missing GMAIL_APP_PASSWORD")
    return errors


def main() -> None:
    errors = validate_configuration()
    if errors:
        for error in errors:
            logger.error(error)
        return

    if ADMIN_USER_ID == 0 and not ALLOWED_USER_IDS:
        logger.warning(
            "No ADMIN_USER_ID or ALLOWED_USER_IDS configured; bot is open to all users."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("checkgmail", checkgmail_command))
    app.add_handler(CommandHandler("fetchlink", fetchlink_command))
    app.add_handler(CommandHandler("fetchfrom", fetchfrom_command))

    logger.info("Starting Gmail Link Telegram bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
