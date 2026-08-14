import smtplib
from email.message import EmailMessage


class EmailTool:
    def __init__(self, smtp_host, smtp_port, username, password):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send_email(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as smtp:
            smtp.login(self.username, self.password)
            smtp.send_message(msg)
