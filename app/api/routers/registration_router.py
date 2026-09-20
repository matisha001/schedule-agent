"""报名路由：队伍/选手管理 + 我的赛事。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUser, get_tournament_service
from app.api.schemas.registration_schema import (
    PlayerCreate,
    PlayerStatusUpdate,
    TeamCreate,
    TeamStatusUpdate,
)
from app.services.tournament_service import TournamentService

registration_router = APIRouter(prefix="/api", tags=["registration"])


@registration_router.get("/me/tournaments")
async def my_tournaments(
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.my_tournaments(user.id)


@registration_router.get("/tournaments/{tournament_id}/teams")
async def list_teams(
    tournament_id: int,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.list_teams(tournament_id)


@registration_router.post("/tournaments/{tournament_id}/teams")
async def create_team(
    tournament_id: int,
    payload: TeamCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.create_team(user.id, tournament_id, payload.model_dump())


@registration_router.post("/tournaments/{tournament_id}/admin-teams")
async def create_team_by_organizer(
    tournament_id: int,
    payload: TeamCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """办赛者代报名：为赛事添加队伍。"""
    return await service.create_team_by_organizer(user.id, tournament_id, payload.model_dump())


@registration_router.patch("/teams/{team_id}/status")
async def update_team_status(
    team_id: int,
    payload: TeamStatusUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.update_team_status(user.id, team_id, payload.status)


@registration_router.delete("/teams/{team_id}", status_code=204)
async def delete_team(
    team_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    await service.delete_team(user.id, team_id)


@registration_router.post("/teams/{team_id}/players")
async def add_player(
    team_id: int,
    payload: PlayerCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.add_player(user.id, team_id, payload.nickname, payload.is_captain)


@registration_router.patch("/players/{player_id}/captain")
async def set_player_captain(
    player_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """办赛者把某队员设为队长（同队其他人自动降级）。"""
    return await service.set_captain(user.id, player_id)


@registration_router.patch("/players/{player_id}/status")
async def update_player_status(
    player_id: int,
    payload: PlayerStatusUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    return await service.update_player_status(user.id, player_id, payload.status)


@registration_router.delete("/players/{player_id}", status_code=204)
async def delete_player(
    player_id: int,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    await service.delete_player(user.id, player_id)
