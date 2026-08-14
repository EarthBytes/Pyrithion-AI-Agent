from fastapi import FastAPI
from app.agents import data, executor, ml, planner, research, writer
from app.config import settings
from app.logging.logger import setup_logger
from app.models.llm_client import LLMClient
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import TaskStore
from app.routes import tasks
from app.tools import email, ml_tools, rag, sql
from app.tools.filesystem import FilesystemTool
logger = setup_logger()

def create_app() -> FastAPI:
    app = FastAPI(title="Email Report Agent")

    llm = LLMClient()
    sql_tool = sql.SQLTool(dsn=settings.database_url)
    ml_tool = ml_tools.MLTools(
        ocsvm_path=settings.ocsvm_model_path,
        reg_path=settings.regression_model_path,
    )
    rag_tool = rag.RAGTool()
    email_tool = email.EmailTool(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
    )
    fs_tool = FilesystemTool(base_dir=settings.reports_dir)

    agents = {
        "planner": planner.PlannerAgent(llm_client=llm),
        "data": data.DataAgent(
            sql_tool=sql_tool,
            llm_client=llm,
            schema_text=settings.db_schema_text,
        ),
        "ml": ml.MLAgent(ml_tools=ml_tool, llm_client=llm),
        "research": research.ResearchAgent(rag_tool=rag_tool, llm_client=llm),
        "writer": writer.WriterAgent(llm_client=llm),
        "executor": executor.ExecutorAgent(email_tool=email_tool, llm_client=llm),
    }

    task_store = TaskStore()
    orchestrator = Orchestrator(agents=agents, filesystem_tool=fs_tool, logger=logger)
    tasks.router.orchestrator = orchestrator
    tasks.router.task_store = task_store
    app.include_router(tasks.router, prefix="/api")

    logger.info("Application started")
    return app

app = create_app()
