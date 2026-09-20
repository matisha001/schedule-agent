"""FastAPI 依赖注入：组装 QueryService（各 Repository 均为模块级单例）+ 登录态依赖。"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.clients.embedding_client_manager import embedding_client_manager
from app.core.security import verify_token
from app.entities.app_user_info import AppUserInfo
from app.repositories.es.value_es_repository import value_es_repository
from app.repositories.mysql.dw.dw_mysql_repository import (
    dw_mysql_repository,
)
from app.repositories.mysql.meta.meta_mysql_repository import meta_mysql_repository
from app.repositories.qdrant.column_qdrant_repository import column_qdrant_repository
from app.repositories.qdrant.metric_qdrant_repository import metric_qdrant_repository
from app.services.query_service import QueryService
from app.services.tournament_service import TournamentService, tournament_service


def get_query_service() -> QueryService:
    return QueryService(
        meta_mysql_repository=meta_mysql_repository,
        embedding_client=embedding_client_manager.client,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
    )


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AppUserInfo:
    """解析 Authorization: Bearer <token>，返回当前登录用户；失败抛 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    uid = verify_token(authorization.removeprefix("Bearer ").strip())
    if uid is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = await dw_mysql_repository.get_user(uid)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AppUserInfo | None:
    """可选登录态：未登录返回 None，不抛错（用于公开接口展示个人相关数据）。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    uid = verify_token(authorization.removeprefix("Bearer ").strip())
    if uid is None:
        return None
    return await dw_mysql_repository.get_user(uid)


CurrentUser = Annotated[AppUserInfo, Depends(get_current_user)]
OptionalUser = Annotated[AppUserInfo | None, Depends(get_optional_user)]


def get_tournament_service() -> TournamentService:
    return tournament_service
