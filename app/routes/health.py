from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    checks: dict[str, str] = {}
    overall = "ok"

    sql_tool = getattr(router, "sql_tool", None)
    if sql_tool is not None and getattr(sql_tool, "pool", None) is not None:
        try:
            async with sql_tool.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"error: {exc}"
            overall = "degraded"
    else:
        checks["postgres"] = "skipped"

    try:
        from app.memory.qdrant_client import QdrantMemoryClient

        client = QdrantMemoryClient(url=settings.qdrant_url)
        client.client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
