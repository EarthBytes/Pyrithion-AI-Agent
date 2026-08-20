import numpy as np

from .base import AgentContext, BaseAgent

ML_PROMPT = """
You are an ML analysis agent.
You receive structured data and a task description.
You must:
- decide whether anomaly detection or trend analysis is appropriate
- interpret the model outputs
- summarise findings in clear language.

Return a textual summary only.
"""


def extract_numeric_series(rows: list[dict]) -> tuple[str, list[float]]:
    """Pick the first numeric column present in the result rows."""
    if not rows:
        raise ValueError("No data rows available for ML analysis")

    sample = rows[0]
    for key, value in sample.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            series = []
            for row in rows:
                cell = row.get(key)
                if isinstance(cell, bool) or not isinstance(cell, (int, float)):
                    break
                series.append(float(cell))
            else:
                return key, series

    raise ValueError(
        "No numeric column found in query results for ML analysis. "
        f"Available columns: {', '.join(sample.keys())}"
    )


class MLAgent(BaseAgent):
    name = "ml"
    description = "Runs anomaly/trend analysis and explains results."

    def __init__(self, ml_tools, llm_client):
        super().__init__(tools={"ml": ml_tools}, llm_client=llm_client)

    async def run(self, context: AgentContext) -> AgentContext:
        step = context.data["current_step"]
        task_desc = step["description"]

        data_results = context.data.get("data_results") or []
        if not data_results:
            raise ValueError("ML agent requires prior data_results from the data agent")

        last_data = data_results[-1]["rows"]
        column, values = extract_numeric_series(last_data)
        X = np.array(values).reshape(-1, 1)

        anomalies = self.tools["ml"].detect_anomalies(X)
        predictions = self.tools["ml"].predict(X)
        context.data.setdefault("ml_raw", []).append(
            {
                "step": task_desc,
                "column": column,
                "values": values,
                "anomalies": anomalies.tolist(),
                "predictions": (
                    predictions.tolist() if hasattr(predictions, "tolist") else list(predictions)
                ),
            }
        )

        prompt = f"""
{ML_PROMPT}

Task:
{task_desc}

Numeric column analysed:
{column}

Values (sample):
{values[:20]}

Anomaly flags (sample):
{anomalies[:20].tolist()}

Trend predictions (sample):
{list(predictions)[:20]}
"""
        summary = await self.llm.call_text(prompt)
        context.data.setdefault("ml_summaries", []).append(
            {"step": task_desc, "summary": summary, "column": column}
        )
        context.logs.append({"agent": self.name, "event": "ml_analysis_done", "column": column})
        return context
