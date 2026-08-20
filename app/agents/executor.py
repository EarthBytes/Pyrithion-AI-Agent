from .base import BaseAgent, AgentContext

EXECUTOR_PROMPT = """
You are an executor agent for an email report generator.
Given the user goal and the final report, decide an appropriate email subject line.

Return JSON:
{"subject": "..."}
"""

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

        email_tool = self.tools["email"]
        if hasattr(email_tool, "send_email_async"):
            await email_tool.send_email_async(
                to=context.user_email,
                subject=subject,
                body=report,
            )
        else:
            email_tool.send_email(
                to=context.user_email,
                subject=subject,
                body=report,
            )
        context.logs.append({"agent": self.name, "event": "email_sent", "to": context.user_email})
        return context
