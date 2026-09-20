"""赛事管理 Agent 入口。启动：uv run uvicorn main:app --reload"""

from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router

app = FastAPI(title="Tournament Agent", version="0.1.0", lifespan=lifespan)
app.include_router(query_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
