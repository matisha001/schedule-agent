"""办赛申请路由（玩家 → 办赛者）：提交申请 + 查询我的申请状态。"""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUser
from app.api.schemas.auth_schema import ApplicationCreateSchema, OrganizerApplicationOut
from app.entities.app_user_info import AppUserInfo
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository as repo

application_router = APIRouter(prefix="/api/apply", tags=["apply"])


def _out(app) -> OrganizerApplicationOut:
    return OrganizerApplicationOut(
        id=app.id,
        user_id=app.user_id,
        status=app.status,
        reason=app.reason,
        reviewed_by=app.reviewed_by,
        reviewed_at=app.reviewed_at,
        created_at=app.created_at,
    )


@application_router.post("/organizer", response_model=OrganizerApplicationOut)
async def apply_organizer(payload: ApplicationCreateSchema, user: CurrentUser):
    """玩家申请成为办赛者（仅 player 可申请；已有待审申请时不可重复提交）。"""
    if user.role != "player":
        raise HTTPException(status_code=400, detail="仅玩家角色可申请成为办赛者")
    latest = await repo.find_latest_application_by_user(user.id)
    if latest is not None and latest.status == "PENDING":
        raise HTTPException(status_code=409, detail="已有待审批的申请，请勿重复提交")
    app = await repo.create_organizer_application(user.id, (payload.reason or "").strip() or None)
    out = _out(app)
    out.nickname = user.nickname
    return out


@application_router.get("/status", response_model=OrganizerApplicationOut | None)
async def apply_status(user: CurrentUser):
    """我的最新办赛申请状态（无申请返回 null）。"""
    app = await repo.find_latest_application_by_user(user.id)
    if app is None:
        return None
    out = _out(app)
    out.nickname = user.nickname
    return out
