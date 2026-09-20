"""对局路由：赛程/对局管理。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, get_tournament_service
from app.api.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate
from app.services.tournament_service import TournamentService

schedule_router = APIRouter(prefix="/api", tags=["schedule"])


@schedule_router.get("/tournaments/{tournament_id}/schedules")
async def list_schedules(
    tournament_id: int,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.list_schedules(tournament_id)


@schedule_router.post("/tournaments/{tournament_id}/schedules")
async def create_schedule(
    tournament_id: int,
    payload: ScheduleCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.create_schedule(user.id, tournament_id, payload.model_dump())


@schedule_router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.update_schedule(user.id, schedule_id, payload.model_dump())


@schedule_router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    await service.delete_schedule(user.id, schedule_id)
