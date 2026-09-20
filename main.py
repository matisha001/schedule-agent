"""赛事管理 Agent 入口。启动：uv run uvicorn main:app --reload"""

from fastapi import FastAPI

from app.api.lifespan import lifespan
from app.api.routers.auth_router import auth_router
from app.api.routers.query_router import query_router
from app.api.routers.registration_router import registration_router
from app.api.routers.schedule_router import schedule_router
from app.api.routers.tournament_router import tournament_router

app = FastAPI(title="Tournament Agent", version="0.1.0", lifespan=lifespan)
app.include_router(query_router)
app.include_router(auth_router)
app.include_router(tournament_router)
app.include_router(registration_router)
app.include_router(schedule_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
