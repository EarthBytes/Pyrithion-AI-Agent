from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.email import ResendEmailTool, build_email_tool


@pytest.mark.asyncio
async def test_resend_send_email_async():
    tool = ResendEmailTool(
        api_key="re_test",
        from_name="Pyrithion AI",
        from_email="onboarding@resend.dev",
    )
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = '{"id":"abc"}'

    with patch("app.tools.email.httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = mock_response
        client_cls.return_value = client

        await tool.send_email_async(
            "recipient@example.com",
            "Test",
            "Body",
            html_body="<p>Hi</p>",
            attachments=[("report.txt", b"data", "text/plain")],
        )

    client.post.assert_called_once()
    call_kwargs = client.post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer re_test"
    assert call_kwargs["json"]["to"] == ["recipient@example.com"]


def test_build_email_tool_uses_resend_when_configured():
    from app.config import Settings

    tool = build_email_tool(
        Settings(
            email_provider="resend",
            resend_api_key="re_test",
            smtp_from_name="Pyrithion AI",
            smtp_from_email="onboarding@resend.dev",
        )
    )
    assert isinstance(tool, ResendEmailTool)
