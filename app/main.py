from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException

from app.agents import data, executor, ml, planner, research, writer
from app.config import settings
from app.errors import AppError, app_error_handler, http_exception_handler, unhandled_exception_handler
from app.logging.logger import setup_logger
from app.models.llm_client import LLMClient
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import build_task_store
from app.routes import health, tasks
from app.tools import email, ml_tools, rag, sql
from app.tools.filesystem import FilesystemTool

logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    sql_tool: sql.SQLTool = app.state.sql_tool
    try:
        await sql_tool.connect()
        logger.info("Database pool ready")
    except Exception as exc:
        logger.warning("Could not create DB pool: %s", exc)

    app.state.task_store = await build_task_store(sql_tool.pool)
    tasks.router.task_store = app.state.task_store
    health.router.sql_tool = sql_tool
    yield
    await sql_tool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Multi-Agent Research & Automation System", lifespan=lifespan)

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

    orchestrator = Orchestrator(agents=agents, filesystem_tool=fs_tool, logger=logger)

    app.state.sql_tool = sql_tool
    app.state.orchestrator = orchestrator

    tasks.router.orchestrator = orchestrator
    tasks.router.task_store = None  # set during lifespan
    health.router.sql_tool = sql_tool

    app.include_router(health.router)
    app.include_router(tasks.router, prefix="/api")

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("Application started")
    return app


app = create_app()
