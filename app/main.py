from fastapi import FastAPI
from app.routes import tasks
from app.orchestrator.orchestrator import Orchestrator
from app.agents import planner, data, ml, research, writer, executor
from app.tools import sql, ml_tools, rag, email
from app.models.llm_client import LLMClient

def create_app():
    app = FastAPI()

    llm = LLMClient(...)
    sql_tool = sql.SQLTool(dsn="postgres://...")
    ml_tool = ml_tools.MLTools(ocsvm_path="models/ocsvm.joblib")
    rag_tool = rag.RAGTool(...)
    email_tool = email.EmailTool(...)

    schema_text = "..."  # describe DB schema

    agents = {
        "planner": planner.PlannerAgent(llm_client=llm),
        "data": data.DataAgent(sql_tool=sql_tool, llm_client=llm, schema_text=schema_text),
        "ml": ml.MLAgent(ml_tools=ml_tool, llm_client=llm),
        "research": research.ResearchAgent(rag_tool=rag_tool, llm_client=llm),
        "writer": writer.WriterAgent(llm_client=llm),
        "executor": executor.ExecutorAgent(email_tool=email_tool, llm_client=llm),
    }

    orchestrator = Orchestrator(agents=agents)
    tasks.router.orchestrator = orchestrator
    app.include_router(tasks.router, prefix="/api")

    return app

app = create_app()
