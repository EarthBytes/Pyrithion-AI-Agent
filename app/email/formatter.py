from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "email"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def render_report_email(
    *,
    subject_goal: str,
    recipient_email: str,
    sources: list[dict] | None = None,
) -> tuple[str, str]:
    """Return (plain_text, html) notification bodies. Report content goes in attachments."""
    context = {
        "goal": subject_goal,
        "recipient_email": recipient_email,
        "sources": sources or [],
        "brand_name": settings.smtp_from_name,
    }
    text = _env.get_template("report.txt").render(**context)
    html = _env.get_template("report.html").render(**context)
    return text, html
