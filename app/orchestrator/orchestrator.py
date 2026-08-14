from app.agents.base import AgentContext

class Orchestrator:
    def __init__(self, agents: dict):
        self.agents = agents

    async def run_task(self, task_id: str, user_goal: str, user_email: str) -> AgentContext:
        context = AgentContext(task_id=task_id, user_goal=user_goal, user_email=user_email)

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

        return context
