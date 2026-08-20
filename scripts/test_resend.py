#!/usr/bin/env python3
"""Quick Resend connectivity test. Usage:
  python scripts/test_resend.py you@example.com
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.tools.email import build_email_tool


async def main() -> None:
    if settings.email_provider != "resend":
        print("Set EMAIL_PROVIDER=resend in .env")
        sys.exit(1)
    if not settings.resend_api_key:
        print("Set RESEND_API_KEY in .env (from https://resend.com/api-keys)")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_resend.py <recipient-email>")
        print("Note: free Resend only delivers to the email you signed up with.")
        sys.exit(1)

    recipient = sys.argv[1]
    tool = build_email_tool()
    await tool.send_email_async(
        to=recipient,
        subject="Pyrithion AI — Resend test",
        body="If you received this, Resend is configured correctly.",
        html_body="<p>If you received this, <strong>Resend</strong> is configured correctly.</p>",
    )
    print(f"Sent test email to {recipient}")


if __name__ == "__main__":
    asyncio.run(main())
