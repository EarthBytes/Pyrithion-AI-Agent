from email.message import EmailMessage

from app.config import settings
from app.tools.email import AGENT_REPLY_HEADER
from app.workers.email_inbox import _should_skip_message


def _make_message(**headers: str) -> EmailMessage:
    msg = EmailMessage()
    for key, value in headers.items():
        msg[key.replace("_", "-")] = value
    return msg


def test_skip_agent_reply_header():
    msg = _make_message(**{AGENT_REPLY_HEADER: "1"})
    skip, reason = _should_skip_message(msg)
    assert skip is True
    assert reason == "agent reply header"


def test_skip_auto_submitted():
    msg = _make_message(Auto_Submitted="auto-replied")
    skip, reason = _should_skip_message(msg)
    assert skip is True
    assert reason == "auto-submitted"


def test_skip_self_reply(monkeypatch):
    monkeypatch.setattr(settings, "smtp_username", "agent@example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "")
    monkeypatch.setattr(settings, "imap_username", "")

    msg = _make_message(
        From="Pyrithion AI <agent@example.com>",
        Subject="Re: Marketing budget",
    )
    skip, reason = _should_skip_message(msg)
    assert skip is True
    assert reason == "self reply"


def test_skip_agent_plain_text_report():
    body = (
        "Pyrithion AI\n\n"
        "Dear User,\n\n"
        "Thank you for your enquiry. Please find your report attached.\n\n"
        "Kind regards,\nPyrithion AI\n"
    )
    msg = EmailMessage()
    msg["Subject"] = "Budget summary"
    msg.set_content(body)
    skip, reason = _should_skip_message(msg)
    assert skip is True


def test_skip_nested_loop_email():
    body = "Your research answer\n====================\n\nQuestion\n--------\n" * 3
    msg = EmailMessage()
    msg["From"] = "agent@example.com"
    msg["Subject"] = "Budget question"
    msg.set_content(body)
    skip, reason = _should_skip_message(msg)
    assert skip is True


def test_does_not_skip_new_user_question(monkeypatch):
    monkeypatch.setattr(settings, "smtp_username", "agent@example.com")
    monkeypatch.setattr(settings, "smtp_from_email", "")
    monkeypatch.setattr(settings, "imap_username", "")

    msg = EmailMessage()
    msg["From"] = "recipient@example.com"
    msg["Subject"] = "What is the marketing budget?"
    msg.set_content("What is the marketing budget in the spreadsheet?")
    skip, _ = _should_skip_message(msg)
    assert skip is False
