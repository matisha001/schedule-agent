"""对局路由：赛程/对局管理。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import CurrentUser, get_tournament_service
from app.api.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate
from app.services.tournament_service import TournamentService

schedule_router = APIRouter(prefix="/api", tags=["schedule"])


@schedule_router.get("/tournaments/{tournament_id}/schedules")
async def list_schedules(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """赛事对局/赛程列表。"""
    return await service.list_schedules(tournament_id)


@schedule_router.post("/tournaments/{tournament_id}/schedules")
async def create_schedule(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: ScheduleCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """创建对局/赛程（办赛者/超管）。"""
    return await service.create_schedule(user.id, tournament_id, payload.model_dump())


@schedule_router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: Annotated[int, Path(gt=0, description="对局 ID")],
    payload: ScheduleUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """更新对局（比分/状态/时间等，办赛者/超管）。"""
    return await service.update_schedule(user.id, schedule_id, payload.model_dump())


@schedule_router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: Annotated[int, Path(gt=0, description="对局 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """删除对局（办赛者/超管）。"""
    await service.delete_schedule(user.id, schedule_id)
