from unittest.mock import MagicMock, patch

from app.tools.email import EmailTool


def test_outlook_smtp_uses_starttls_on_port_587():
    tool = EmailTool(
        smtp_host="smtp-mail.outlook.com",
        smtp_port=587,
        username="agent@example.com",
        password="secret",
        from_name="Pyrithion AI",
        from_email="agent@example.com",
    )

    smtp = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = smtp

    with patch("app.tools.email.smtplib.SMTP", return_value=smtp_ctx) as smtp_cls:
        tool.send_email("recipient@example.com", "Test", "Body")

    smtp_cls.assert_called_once_with("smtp-mail.outlook.com", 587)
    smtp.ehlo.assert_called()
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("agent@example.com", "secret")
    smtp.send_message.assert_called_once()


def test_smtp_ssl_used_on_port_465():
    tool = EmailTool(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        username="sender@example.com",
        password="secret",
    )

    smtp = MagicMock()
    smtp_ctx = MagicMock()
    smtp_ctx.__enter__.return_value = smtp

    with patch("app.tools.email.smtplib.SMTP_SSL", return_value=smtp_ctx) as smtp_cls:
        tool.send_email("recipient@example.com", "Test", "Body")

    smtp_cls.assert_called_once_with("smtp.gmail.com", 465)
    smtp.login.assert_called_once()
    smtp.send_message.assert_called_once()
