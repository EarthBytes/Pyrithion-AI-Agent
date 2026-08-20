from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql://localhost:5432/analytics"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "docs"
    qdrant_api_key: str | None = None

    llm_provider: str = "openrouter"
    llm_api_key: str = ""
    llm_model: str = "google/gemini-flash-1.5"
    ollama_base_url: str = "http://localhost:11434"

    # Outbound email (separate from Google Drive / service account auth)
    # email_provider: smtp (Gmail app password) | resend (free API, no Outlook SMTP)
    email_provider: str = "smtp"
    resend_api_key: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Pyrithion AI"
    smtp_from_email: str = ""

    # Optional inbound email — keep disabled until outbound is verified
    imap_enabled: bool = False
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_poll_seconds: int = 60
    imap_allowed_senders: str = ""  # comma-separated; empty = allow anyone

    # Optional: sync documents from Google Drive into Qdrant
    google_drive_folder_id: str = ""
    google_service_account_file: str = ""
    drive_sync_on_startup: bool = True

    ocsvm_model_path: str | None = None
    regression_model_path: str | None = None
    reports_dir: str = "reports"

    api_key: str = ""
    sql_allowed_tables: str = "energy_usage,revenue,users"
    sql_row_limit: int = 500
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 384
    embedding_provider: str = "local"  # local | api | sentence-transformers
    db_pool_min: int = 1
    db_pool_max: int = 10

    db_schema_text: str = """
Tables:
  energy_usage (id, timestamp, value, unit, site_id)
  revenue (id, date, amount, region, product)
  users (id, created_at, churned, plan)
"""

    @property
    def allowed_tables(self) -> set[str]:
        return {t.strip().lower() for t in self.sql_allowed_tables.split(",") if t.strip()}

    @property
    def imap_allowed_sender_set(self) -> set[str]:
        return {
            s.strip().lower()
            for s in self.imap_allowed_senders.split(",")
            if s.strip()
        }

    @property
    def drive_configured(self) -> bool:
        if not (self.google_drive_folder_id and self.google_service_account_file):
            return False
        return Path(self.google_service_account_file).exists()

    @property
    def email_configured(self) -> bool:
        if self.email_provider == "resend":
            return bool(self.resend_api_key and self.smtp_from_address)
        return bool(self.smtp_username and self.smtp_password)

    @property
    def smtp_from_address(self) -> str:
        return self.smtp_from_email or self.smtp_username

    def smtp_config_warnings(self) -> list[str]:
        warnings: list[str] = []
        username = self.smtp_username.lower()
        from_addr = self.smtp_from_address.lower()
        host = self.smtp_host.lower()

        if not self.smtp_username:
            warnings.append("SMTP_USERNAME is not set.")
        if "outlook" in host or "office365" in host:
            if "gmail.com" in username:
                warnings.append(
                    "SMTP_USERNAME is still a Gmail address but SMTP_HOST is Outlook. "
                    "Set SMTP_USERNAME to your sender address (e.g. agent@example.com)."
                )
            if from_addr and username and from_addr != username:
                warnings.append(
                    "SMTP_FROM_EMAIL differs from SMTP_USERNAME. Outlook sends as the login account."
                )
        return warnings


settings = Settings()
