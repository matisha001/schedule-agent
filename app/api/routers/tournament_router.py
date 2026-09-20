"""赛事路由：创建/列表/详情/更新/删除/状态流转 + 阶段管理。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

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
    return await service.create_tournament(user.id, payload.model_dump())


@tournament_router.get("")
async def list_tournaments(
    scope: str = Query(default="published", pattern="^(published|mine)$"),
    user: OptionalUser = None,
    service: Annotated[TournamentService, Depends(get_tournament_service)] = None,
):
    uid = user.id if user is not None else None
    return await service.list_tournaments(scope, uid)


@tournament_router.get("/{tournament_id}")
async def get_tournament(
    tournament_id: int,
    user: OptionalUser = None,
    service: Annotated[TournamentService, Depends(get_tournament_service)] = None,
):
    uid = user.id if user is not None else None
    return await service.get_tournament_detail(tournament_id, uid)


@tournament_router.put("/{tournament_id}")
async def update_tournament(
    tournament_id: int,
    payload: TournamentUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.update_tournament(user.id, tournament_id, payload.model_dump())


@tournament_router.delete("/{tournament_id}", status_code=204)
async def delete_tournament(
    tournament_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    await service.delete_tournament(user.id, tournament_id)


@tournament_router.post("/{tournament_id}/transition")
async def transition_tournament(
    tournament_id: int,
    payload: TransitionAction,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.transition(user.id, tournament_id, payload.action)


# ---------- 阶段 ----------
@tournament_router.get("/{tournament_id}/phases")
async def list_phases(
    tournament_id: int,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.list_phases(tournament_id)


@tournament_router.post("/{tournament_id}/phases")
async def create_phase(
    tournament_id: int,
    payload: PhaseCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.create_phase(user.id, tournament_id, payload.model_dump())


@tournament_router.put("/phases/{phase_id}")
async def update_phase(
    phase_id: int,
    payload: PhaseUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.update_phase(user.id, phase_id, payload.model_dump())


@tournament_router.delete("/phases/{phase_id}", status_code=204)
async def delete_phase(
    phase_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    await service.delete_phase(user.id, phase_id)
