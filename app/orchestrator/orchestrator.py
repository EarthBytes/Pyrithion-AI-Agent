import logging
from app.agents.base import AgentContext

class Orchestrator:
    def __init__(self, agents: dict, filesystem_tool=None, logger: logging.Logger | None = None):
        self.agents = agents
        self.filesystem_tool = filesystem_tool
        self.logger = logger or logging.getLogger("app")

    async def run_task(self, task_id: str, user_goal: str, user_email: str) -> AgentContext:
        context = AgentContext(task_id=task_id, user_goal=user_goal, user_email=user_email)
        self.logger.info(
            "Starting task",
            extra={"extra_fields": {"task_id": task_id, "goal": user_goal}},
        )

        # 1. planning
        planner = self.agents["planner"]
        context = await planner.run(context)
        plan = context.data["plan"]

        # 2. execute steps
        for step in plan:
            agent_name = step["agent"]
            context.data["current_step"] = step
            agent = self.agents[agent_name]
            context = await agent.run(context)
            self.logger.info(
                "Step completed",
                extra={"extra_fields": {"task_id": task_id, "agent": agent_name}},
            )

        report = context.data.get("final_report")
        if report and self.filesystem_tool:
            path = self.filesystem_tool.save_report(task_id, report)
            context.logs.append({"event": "report_saved", "path": str(path)})

        return context
