"""SSE 流式问数路由 + 预制提示词（按登录态/角色过滤）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import OptionalUser, get_query_service
from app.api.schemas.query_schema import PresetQueryOut, PresetQueryParam, QuerySchema
from app.conf.preset_queries import filter_by_role
from app.entities.app_user_info import AppUserInfo
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query_handler(
    payload: QuerySchema,
    query_service: Annotated[QueryService, Depends(get_query_service)],
    user: OptionalUser,
):
    """问数：可选登录（未登录 = guest 仅公开数据），权限上下文随请求注入。"""
    return StreamingResponse(
        query_service.query(payload.query, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@query_router.get("/api/query/presets", response_model=list[PresetQueryOut])
async def query_presets(user: OptionalUser):
    """预制提示词：服务端按「登录态 + 角色」过滤，未登录只返回 guest 组的 4 条。"""
    role = user.role if user else "guest"
    items = filter_by_role(role)
    return [
        PresetQueryOut(
            id=p["id"],
            title=p["title"],
            template=p["template"],
            params=[
                PresetQueryParam(key=param["key"], source=param.get("source", "tournaments"))
                for param in p.get("params") or []
            ],
        )
        for p in items
    ]
