"""管理后台路由（仅 super_admin）：用户列表 / 修改角色（保护最后一名超管）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.dependencies import require_role
from app.api.schemas.auth_schema import (
    AdminUserListOut,
    AdminUserOut,
    ApplicationListOut,
    ApplicationReviewSchema,
    OrganizerApplicationOut,
    UpdateRoleSchema,
)
from app.core.bootstrap import SUPER_ADMIN_ROLE
from app.entities.app_user_info import AppUserInfo
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository as repo

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# 用户管理接口统一要求超管角色
SuperAdmin = Annotated[AppUserInfo, Depends(require_role(SUPER_ADMIN_ROLE))]
# 办赛申请审批：超管 / 运营
Reviewer = Annotated[AppUserInfo, Depends(require_role(SUPER_ADMIN_ROLE, "operator"))]


def _user_out(user: AppUserInfo) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        nickname=user.nickname,
        phone=user.phone,
        role=user.role,
        created_at=user.created_at,
    )


@admin_router.get("/users", response_model=AdminUserListOut)
async def list_users(
    _: SuperAdmin,
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    users = await repo.list_users(limit=size, offset=(page - 1) * size)
    total = await repo.count_users()
    return AdminUserListOut(total=total, page=page, size=size, items=[_user_out(u) for u in users])


@admin_router.patch("/users/{user_id}/role", response_model=AdminUserOut)
async def update_user_role(
    user_id: Annotated[int, Path(gt=0, description="目标用户 ID")],
    payload: UpdateRoleSchema,
    operator: SuperAdmin,
):
    """修改用户角色。保护规则：最后一名超管不可被降级。"""
    target = await repo.get_user(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    if target.role == SUPER_ADMIN_ROLE and payload.role != SUPER_ADMIN_ROLE:
        super_count = await repo.count_users_by_role(SUPER_ADMIN_ROLE)
        if super_count <= 1:
            raise HTTPException(status_code=403, detail="系统至少保留一名超级管理员，不可降级最后一名超管")

    updated = await repo.update_user_role(user_id, payload.role)
    return _user_out(updated)


def _application_out(app, applicant: AppUserInfo | None) -> OrganizerApplicationOut:
    return OrganizerApplicationOut(
        id=app.id,
        user_id=app.user_id,
        nickname=applicant.nickname if applicant else "",
        status=app.status,
        reason=app.reason,
        reviewed_by=app.reviewed_by,
        reviewed_at=app.reviewed_at,
        created_at=app.created_at,
    )


@admin_router.get("/applications", response_model=ApplicationListOut)
async def list_applications(
    _: Reviewer,
    status: str | None = Query(None, pattern="^(PENDING|APPROVED|REJECTED)$", description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """办赛申请列表（超管/运营），按申请时间倒序。"""
    applications = await repo.list_organizer_applications(
        status=status, limit=size, offset=(page - 1) * size
    )
    total = await repo.count_organizer_applications(status=status)
    items = []
    for app in applications:
        applicant = await repo.get_user(app.user_id)
        items.append(_application_out(app, applicant))
    return ApplicationListOut(total=total, page=page, size=size, items=items)


@admin_router.post("/applications/{app_id}/review", response_model=OrganizerApplicationOut)
async def review_application(
    app_id: int,
    payload: ApplicationReviewSchema,
    reviewer: Reviewer,
):
    """审批办赛申请：通过则把申请人升级为办赛者（organizer），驳回则保持原角色。"""
    app = await repo.get_organizer_application(app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if app.status != "PENDING":
        raise HTTPException(status_code=400, detail="该申请已处理，不能重复审批")

    new_status = "APPROVED" if payload.approve else "REJECTED"
    reviewed = await repo.review_organizer_application(app_id, new_status, reviewer.id)
    applicant = await repo.get_user(app.user_id)

    if payload.approve and applicant is not None and applicant.role == "player":
        # 通过审批：玩家角色升级为办赛者
        await repo.update_user_role(app.user_id, "organizer")

    return _application_out(reviewed, applicant)
