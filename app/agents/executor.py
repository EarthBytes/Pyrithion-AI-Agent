from .base import AgentContext, BaseAgent
from app.config import settings
from app.email.attachments import build_report_attachments
from app.email.formatter import render_report_email
from app.utils.prompts import EXECUTOR_PROMPT


class ExecutorAgent(BaseAgent):
    name = "executor"
    description = "Delivers the report via email."

    def __init__(self, email_tool, llm_client):
        super().__init__(tools={"email": email_tool}, llm_client=llm_client)

    async def run(self, context: AgentContext) -> AgentContext:
        report = context.data["final_report"]
        prompt = f"""
{EXECUTOR_PROMPT}

User goal:
{context.user_goal}

Report (excerpt):
{report[:1000]}
"""
        decision = await self.llm.call_json(prompt)
        subject = decision["subject"]

        sources = []
        for item in context.data.get("research_context", []):
            for doc in item.get("docs", []):
                sources.append(
                    {
                        "filename": doc.get("filename") or doc.get("metadata", {}).get("filename"),
                        "score": doc.get("score"),
                    }
                )

        attachments = build_report_attachments(
            task_id=context.task_id,
            goal=context.user_goal,
            report_body=report,
            sources=sources,
            brand_name=settings.smtp_from_name,
        )
        text_body, html_body = render_report_email(
            subject_goal=context.user_goal,
            recipient_email=context.user_email,
            sources=sources,
        )

        email_tool = self.tools["email"]
        send_kwargs = {
            "to": context.user_email,
            "subject": subject,
            "body": text_body,
            "html_body": html_body,
            "attachments": attachments,
        }
        if hasattr(email_tool, "send_email_async"):
            await email_tool.send_email_async(**send_kwargs)
        else:
            email_tool.send_email(**send_kwargs)

        context.logs.append(
            {
                "agent": self.name,
                "event": "email_sent",
                "to": context.user_email,
                "attachments": [name for name, _, _ in attachments],
            }
        )
        return context
