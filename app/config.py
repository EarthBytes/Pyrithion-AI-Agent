from pydantic_settings import BaseSettings, SettingsConfigDict


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

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""

    ocsvm_model_path: str | None = None
    regression_model_path: str | None = None
    reports_dir: str = "reports"

    db_schema_text: str = """
Tables:
  energy_usage (id, timestamp, value, unit, site_id)
  revenue (id, date, amount, region, product)
  users (id, created_at, churned, plan)
"""


settings = Settings()
