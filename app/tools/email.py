import asyncio
import base64
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from app.config import Settings, settings

AGENT_REPLY_HEADER = "X-Research-Agent-Reply"


class EmailTool:
    def __init__(
        self,
        smtp_host,
        smtp_port,
        username,
        password,
        from_name: str = "Pyrithion AI",
        from_email: str | None = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_name = from_name
        self.from_email = from_email or username

    def _from_header(self) -> str:
        return formataddr((self.from_name, self.from_email))

    def _send_via_smtp(self, msg: EmailMessage) -> None:
        try:
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
                    smtp.login(self.username, self.password)
                    smtp.send_message(msg)
                return

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.username, self.password)
                smtp.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            detail = exc.smtp_error.decode(errors="ignore") if exc.smtp_error else str(exc)
            if "SmtpClientAuthentication is disabled" in detail:
                raise RuntimeError(
                    "Personal Outlook accounts cannot use SMTP (Microsoft blocks it). "
                    "Use Gmail SMTP (app password) or set EMAIL_PROVIDER=resend in .env. "
                    "Google Drive stays on your service account — only outbound send changes."
                ) from exc
            raise RuntimeError(
                f"SMTP login failed for {self.username}: {detail}"
            ) from exc

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> None:
        msg = EmailMessage()
        msg["From"] = self._from_header()
        msg["To"] = to
        msg["Subject"] = subject
        msg[AGENT_REPLY_HEADER] = "1"
        msg["Auto-Submitted"] = "auto-replied"
        msg["Precedence"] = "bulk"
        msg.set_content(body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        for filename, data, mime_type in attachments or []:
            maintype, _, subtype = mime_type.partition("/")
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype or "octet-stream",
                filename=filename,
            )

        self._send_via_smtp(msg)

    async def send_email_async(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> None:
        await asyncio.to_thread(
            self.send_email, to, subject, body, html_body, attachments
        )


class ResendEmailTool:
    """Send via Resend HTTP API — works without Microsoft/Google SMTP."""

    def __init__(
        self,
        api_key: str,
        from_name: str,
        from_email: str,
    ):
        self.api_key = api_key
        self.from_name = from_name
        self.from_email = from_email

    async def send_email_async(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> None:
        payload: dict = {
            "from": formataddr((self.from_name, self.from_email)),
            "to": [to],
            "subject": subject,
            "text": body,
            "headers": {
                AGENT_REPLY_HEADER: "1",
                "Auto-Submitted": "auto-replied",
            },
        }
        if html_body:
            payload["html"] = html_body
        if attachments:
            payload["attachments"] = [
                {
                    "filename": filename,
                    "content": base64.b64encode(data).decode("ascii"),
                }
                for filename, data, _ in attachments
            ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=30.0,
            )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Resend API error ({response.status_code}): {response.text}"
            )

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> None:
        asyncio.run(
            self.send_email_async(to, subject, body, html_body, attachments)
        )


def build_email_tool(cfg: Settings | None = None):
    cfg = cfg or settings
    if cfg.email_provider == "resend":
        return ResendEmailTool(
            api_key=cfg.resend_api_key,
            from_name=cfg.smtp_from_name,
            from_email=cfg.smtp_from_address,
        )
    return EmailTool(
        smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port,
        username=cfg.smtp_username,
        password=cfg.smtp_password,
        from_name=cfg.smtp_from_name,
        from_email=cfg.smtp_from_address,
    )
