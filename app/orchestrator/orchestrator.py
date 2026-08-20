import logging

from app.agents.base import AgentContext

ALLOWED_AGENTS = {"planner", "data", "ml", "research", "writer", "executor"}


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

        planner = self.agents["planner"]
        context = await planner.run(context)
        plan = context.data.get("plan") or []
        if not isinstance(plan, list) or not plan:
            raise ValueError("Planner returned an empty or invalid plan")

        plan = self._normalize_plan(plan)
        context.data["plan"] = plan

        for step in plan:
            agent_name = step["agent"]
            if agent_name not in self.agents:
                raise ValueError(f"Unknown agent in plan: {agent_name}")
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

    def _normalize_plan(self, plan: list[dict]) -> list[dict]:
        cleaned: list[dict] = []
        for step in plan:
            agent = str(step.get("agent", "")).strip().lower()
            if agent == "planner":
                continue
            if agent not in ALLOWED_AGENTS - {"planner"}:
                raise ValueError(f"Invalid agent name in plan: {agent}")
            cleaned.append(
                {
                    "agent": agent,
                    "description": step.get("description") or f"Run {agent}",
                }
            )

        if not cleaned:
            raise ValueError("Plan has no executable steps")

        # Ensure writer then executor finish the pipeline when those agents exist.
        available = set(self.agents)
        agents_in_plan = [s["agent"] for s in cleaned]
        if "writer" in available and "writer" not in agents_in_plan:
            cleaned.append({"agent": "writer", "description": "Write final report"})
        if "executor" in available and "executor" not in agents_in_plan:
            cleaned.append({"agent": "executor", "description": "Email report"})
        elif "executor" in agents_in_plan:
            executor_steps = [s for s in cleaned if s["agent"] == "executor"]
            cleaned = [s for s in cleaned if s["agent"] != "executor"] + executor_steps[-1:]

        return cleaned
