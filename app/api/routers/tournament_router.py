"""赛事路由：创建/列表/详情/更新/删除/状态流转 + 阶段管理。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import (
    CurrentUser,
    OptionalUser,
    get_tournament_service,
)
from app.api.schemas.tournament_schema import (
    PhaseCreate,
    PhaseUpdate,
    TournamentCreate,
    TournamentUpdate,
    TransitionAction,
)
from app.services.tournament_service import TournamentService

tournament_router = APIRouter(prefix="/api/tournaments", tags=["tournament"])


@tournament_router.post("")
async def create_tournament(
    payload: TournamentCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """创建赛事（需登录，办赛者/超管可用）。"""
    return await service.create_tournament(user.id, payload.model_dump())


@tournament_router.get("")
async def list_tournaments(
    scope: str = Query(default="published", pattern="^(published|mine)$", description="查询范围：published(已发布) / mine(我创建的)"),
    user: OptionalUser = None,
    service: Annotated[TournamentService, Depends(get_tournament_service)] = None,
):
    """赛事列表：published 公开可见；mine 需登录返回自己创建的赛事。"""
    uid = user.id if user is not None else None
    return await service.list_tournaments(scope, uid)


@tournament_router.get("/{tournament_id}")
async def get_tournament(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    user: OptionalUser = None,
    service: Annotated[TournamentService, Depends(get_tournament_service)] = None,
):
    """赛事详情：按登录态过滤可见性。"""
    uid = user.id if user is not None else None
    return await service.get_tournament_detail(tournament_id, uid)


@tournament_router.put("/{tournament_id}")
async def update_tournament(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: TournamentUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """更新赛事（办赛者/超管）。"""
    return await service.update_tournament(user.id, tournament_id, payload.model_dump())


@tournament_router.delete("/{tournament_id}", status_code=204)
async def delete_tournament(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """删除赛事（办赛者/超管）。"""
    await service.delete_tournament(user.id, tournament_id)


@tournament_router.post("/{tournament_id}/transition")
async def transition_tournament(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: TransitionAction,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """赛事状态流转：publish/open/close/start/finish。"""
    return await service.transition(user.id, tournament_id, payload.action)


# ---------- 阶段 ----------
@tournament_router.get("/{tournament_id}/phases")
async def list_phases(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """赛事阶段列表。"""
    return await service.list_phases(tournament_id)


@tournament_router.post("/{tournament_id}/phases")
async def create_phase(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: PhaseCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """为赛事创建阶段（办赛者/超管）。"""
    return await service.create_phase(user.id, tournament_id, payload.model_dump())


@tournament_router.put("/phases/{phase_id}")
async def update_phase(
    phase_id: Annotated[int, Path(gt=0, description="阶段 ID")],
    payload: PhaseUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """更新阶段（办赛者/超管）。"""
    return await service.update_phase(user.id, phase_id, payload.model_dump())


@tournament_router.delete("/phases/{phase_id}", status_code=204)
async def delete_phase(
    phase_id: Annotated[int, Path(gt=0, description="阶段 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """删除阶段（办赛者/超管）。"""
    await service.delete_phase(user.id, phase_id)
