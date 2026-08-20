from app.config import Settings


def test_smtp_config_warns_when_gmail_login_with_outlook_host():
    settings = Settings(
        smtp_host="smtp-mail.outlook.com",
        smtp_username="sender@gmail.com",
        smtp_password="secret",
        smtp_from_email="agent@example.com",
    )
    warnings = settings.smtp_config_warnings()
    assert any("Gmail address" in warning for warning in warnings)
