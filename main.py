"""赛事管理 Agent 入口。启动：uv run uvicorn main:app --reload"""

import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.admin_router import admin_router
from app.api.routers.application_router import application_router
from app.api.routers.auth_router import auth_router
from app.api.routers.query_router import query_router
from app.api.routers.registration_router import registration_router
from app.api.routers.schedule_router import schedule_router
from app.api.routers.tournament_router import tournament_router
from app.core.context import request_id_ctx_var

app = FastAPI(title="Tournament Agent", version="0.1.0", lifespan=lifespan)
app.include_router(query_router)
app.include_router(auth_router)
app.include_router(tournament_router)
app.include_router(registration_router)
app.include_router(schedule_router)
app.include_router(admin_router)
app.include_router(application_router)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # 请求被处理之前：为每个 HTTP 请求生成唯一 request_id 并写入上下文，
    # 日志模块会从 ContextVar 读取并注入到该请求链路的每条日志中
    request_id = uuid.uuid4()
    request_id_ctx_var.set(request_id)
    response = await call_next(request)
    # 请求被处理之后
    return response


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
