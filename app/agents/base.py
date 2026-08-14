from abc import ABC, abstractmethod

class AgentContext:
    def __init__(self, task_id, user_goal, user_email, data=None, memory=None, logs=None):
        self.task_id = task_id
        self.user_goal = user_goal
        self.user_email = user_email
        self.data = data or {}
        self.memory = memory or {}
        self.logs = logs or []

class BaseAgent(ABC):
    name: str
    description: str

    def __init__(self, tools=None, llm_client=None):
        self.tools = tools or {}
        self.llm = llm_client

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentContext:
        ...
