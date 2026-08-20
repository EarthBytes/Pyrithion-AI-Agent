"""Background worker: poll IMAP inbox and turn emails into tasks."""

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import re
from email.header import decode_header
from email.utils import parseaddr

from app.config import settings
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import TaskStore
from app.routes.tasks import _run_in_background
from app.tools.email import AGENT_REPLY_HEADER, EmailTool
from app.utils.id_generator import generate_task_id
from app.utils.text import extract_filename_hint

logger = logging.getLogger("app")

SUBJECT_PREFIX = re.compile(r"^\s*(re:|fwd:)\s*", re.IGNORECASE)
AGENT_FOOTER_MARKER = "Pyrithion AI"
AGENT_REPORT_TITLE = "Your research answer"
AGENT_NOTIFICATION_TITLE = "Your report is ready"


def _is_agent_report(subject: str, body: str) -> bool:
    """Detect our own report emails (Gmail often strips custom headers in the inbox)."""
    subject_lower = (subject or "").lower().strip()
    if subject_lower in {AGENT_REPORT_TITLE.lower(), AGENT_NOTIFICATION_TITLE.lower()}:
        return True
    if AGENT_REPORT_TITLE in (subject or "") or AGENT_NOTIFICATION_TITLE in (subject or ""):
        return True

    if not body:
        return False

    if AGENT_FOOTER_MARKER in body:
        return True
    if body.lstrip().startswith(AGENT_REPORT_TITLE):
        return True
    if body.lstrip().startswith(f"{AGENT_FOOTER_MARKER} — Your report is ready"):
        return True
    if "Dear User" in body and "Please find your report attached" in body:
        return True
    if "Kind regards" in body and AGENT_FOOTER_MARKER in body:
        return True
    if "Answer\n------" in body or "Answer\n----" in body:
        return True
    if body.count(AGENT_REPORT_TITLE) >= 2:
        return True
    if "Sorry, your request could not be completed" in body:
        return True
    # HTML template marker; plain-text uses "Question\n--------" instead.
    if "Your question" in body and "Sources" in body:
        return True
    if "Question\n--------" in body and "Answer\n------" in body:
        return True

    return False


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore").strip()
        return ""

    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="ignore").strip()


def _goal_from_email(subject: str, body: str) -> str:
    subject = SUBJECT_PREFIX.sub("", subject).strip()
    if _is_agent_report(subject, body):
        return ""

    if body:
        cleaned = body
        if AGENT_FOOTER_MARKER in cleaned:
            cleaned = cleaned.split(AGENT_FOOTER_MARKER, 1)[0].strip()
        if cleaned:
            return cleaned if len(cleaned) < 500 else cleaned[:500].strip()
    return subject or "Please summarise the latest documents."


def _our_addresses() -> set[str]:
    addresses = {
        (settings.smtp_username or "").lower(),
        (settings.smtp_from_email or "").lower(),
        (settings.imap_username or "").lower(),
    }
    return {addr for addr in addresses if addr}


def _should_skip_message(msg: email.message.Message) -> tuple[bool, str]:
    if msg.get(AGENT_REPLY_HEADER) == "1":
        return True, "agent reply header"

    auto_submitted = (msg.get("Auto-Submitted") or "").lower()
    if auto_submitted.startswith("auto"):
        return True, "auto-submitted"

    subject = _decode_header_value(msg.get("Subject"))
    sender = parseaddr(msg.get("From", ""))[1].lower()
    our_addresses = _our_addresses()

    if sender in our_addresses and SUBJECT_PREFIX.match(subject or ""):
        return True, "self reply"

    body = _extract_body(msg)
    if _is_agent_report(subject, body):
        return True, "agent report email"

    return False, ""


class EmailInboxWorker:
    def __init__(
        self,
        orchestrator: Orchestrator,
        task_store: TaskStore,
        email_tool: EmailTool,
    ):
        self.orchestrator = orchestrator
        self.task_store = task_store
        self.email_tool = email_tool
        self._seen: set[str] = set()
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if not settings.imap_enabled:
            return
        username = settings.imap_username or settings.smtp_username
        password = settings.imap_password or settings.smtp_password
        if not username or not password:
            logger.warning("IMAP enabled but credentials are not set")
            return
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Email inbox worker started for %s", username)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        while True:
            try:
                messages = await asyncio.to_thread(self._fetch_unseen)
                for message in messages:
                    await self._handle_email(**message)
            except Exception:
                logger.exception("Email inbox poll failed")
            await asyncio.sleep(settings.imap_poll_seconds)

    def _fetch_unseen(self) -> list[dict]:
        username = settings.imap_username or settings.smtp_username
        password = settings.imap_password or settings.smtp_password
        allowed = settings.imap_allowed_sender_set

        mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        messages: list[dict] = []
        try:
            mail.login(username, password)
            mail.select("INBOX")
            status, data = mail.search(None, "UNSEEN")
            if status != "OK":
                return messages

            for num in data[0].split():
                status, fetched = mail.fetch(num, "(RFC822)")
                if status != "OK" or not fetched:
                    continue
                raw = fetched[0][1]
                msg = email.message_from_bytes(raw)
                message_id = msg.get("Message-ID", num.decode())

                skip, reason = _should_skip_message(msg)
                if skip:
                    logger.info("Skipping inbound email: %s", reason)
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue

                if message_id in self._seen:
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue

                sender = parseaddr(msg.get("From", ""))[1].lower()
                if allowed and sender not in allowed:
                    logger.info("Skipping email from non-allowlisted sender: %s", sender)
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue

                subject = _decode_header_value(msg.get("Subject"))
                body = _extract_body(msg)
                goal = _goal_from_email(subject, body)
                if not goal:
                    mail.store(num, "+FLAGS", "\\Seen")
                    continue

                self._seen.add(message_id)
                mail.store(num, "+FLAGS", "\\Seen")
                messages.append(
                    {
                        "task_id": generate_task_id(),
                        "goal": goal,
                        "recipient": sender or username,
                        "source_document": extract_filename_hint(goal),
                        "subject": subject or goal[:60],
                    }
                )
        finally:
            try:
                mail.logout()
            except Exception:
                pass
        return messages

    async def _handle_email(
        self,
        task_id: str,
        goal: str,
        recipient: str,
        subject: str,
        source_document: str | None = None,
    ) -> None:
        await self.task_store.persist_create(task_id, goal, recipient)
        await _run_in_background(
            task_id,
            goal,
            recipient,
            self.orchestrator,
            self.task_store,
            source_document=source_document,
        )
