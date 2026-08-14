# app/agents/ml.py
from .base import BaseAgent, AgentContext
import numpy as np

ML_PROMPT = """
You are an ML analysis agent.
You receive structured data and a task description.
You must:
- decide whether anomaly detection or trend analysis is appropriate
- interpret the model outputs
- summarise findings in clear language.

Return a textual summary only.
"""

class MLAgent(BaseAgent):
    name = "ml"
    description = "Runs anomaly/trend analysis and explains results."

    def __init__(self, ml_tools, llm_client):
        super().__init__(tools={"ml": ml_tools}, llm_client=llm_client)

    async def run(self, context: AgentContext) -> AgentContext:
        step = context.data["current_step"]
        task_desc = step["description"]

        last_data = context.data["data_results"][-1]["rows"]
        # adapt feature extraction to your schema
        values = [row["value"] for row in last_data]  # example
        X = np.array(values).reshape(-1, 1)

        anomalies = self.tools["ml"].detect_anomalies(X)
        context.data.setdefault("ml_raw", []).append(
            {"step": task_desc, "values": values, "anomalies": anomalies.tolist()}
        )

        prompt = f"""
{ML_PROMPT}

Task:
{task_desc}

Values (sample):
{values[:20]}

Anomaly flags (sample):
{anomalies[:20].tolist()}
"""
        summary = await self.llm.call_text(prompt)
        context.data.setdefault("ml_summaries", []).append({"step": task_desc, "summary": summary})
        context.logs.append({"agent": self.name, "event": "ml_analysis_done"})
        return context
