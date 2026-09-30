"""报名路由：队伍/选手管理 + 我的赛事。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path

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
    """我参与的赛事列表（需登录）。"""
    return await service.my_tournaments(user.id)


@registration_router.get("/tournaments/{tournament_id}/teams")
async def list_teams(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """赛事队伍列表。"""
    return await service.list_teams(tournament_id)


@registration_router.post("/tournaments/{tournament_id}/teams")
async def create_team(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: TeamCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """选手自主报名：创建队伍（需登录）。"""
    return await service.create_team(user.id, tournament_id, payload.model_dump())


@registration_router.post("/tournaments/{tournament_id}/admin-teams")
async def create_team_by_organizer(
    tournament_id: Annotated[int, Path(gt=0, description="赛事 ID")],
    payload: TeamCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """办赛者代报名：为赛事添加队伍。"""
    return await service.create_team_by_organizer(user.id, tournament_id, payload.model_dump())


@registration_router.patch("/teams/{team_id}/status")
async def update_team_status(
    team_id: Annotated[int, Path(gt=0, description="队伍 ID")],
    payload: TeamStatusUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """更新队伍状态（办赛者审核/选手取消）。"""
    return await service.update_team_status(user.id, team_id, payload.status)


@registration_router.delete("/teams/{team_id}", status_code=204)
async def delete_team(
    team_id: Annotated[int, Path(gt=0, description="队伍 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """删除队伍（办赛者/队长）。"""
    await service.delete_team(user.id, team_id)


@registration_router.post("/teams/{team_id}/players")
async def add_player(
    team_id: Annotated[int, Path(gt=0, description="队伍 ID")],
    payload: PlayerCreate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """为队伍添加选手（需登录）。"""
    return await service.add_player(user.id, team_id, payload.nickname, payload.is_captain)


@registration_router.patch("/players/{player_id}/captain")
async def set_player_captain(
    player_id: Annotated[int, Path(gt=0, description="选手 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """办赛者把某队员设为队长（同队其他人自动降级）。"""
    return await service.set_captain(user.id, player_id)


@registration_router.patch("/players/{player_id}/status")
async def update_player_status(
    player_id: Annotated[int, Path(gt=0, description="选手 ID")],
    payload: PlayerStatusUpdate,
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """更新选手状态（AGREED/REJECTED）。"""
    return await service.update_player_status(user.id, player_id, payload.status)


@registration_router.delete("/players/{player_id}", status_code=204)
async def delete_player(
    player_id: Annotated[int, Path(gt=0, description="选手 ID")],
    user: CurrentUser,
    service: Annotated[TournamentService, Depends(get_tournament_service)],
):
    """删除选手（办赛者/队长）。"""
    await service.delete_player(user.id, player_id)
