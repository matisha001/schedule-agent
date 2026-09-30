"""认证路由：登录 / 资料修改 / 密码修改 / 注销 + 超管首次启动引导创建。"""

import re

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUser
from app.api.schemas.auth_schema import (
    BootstrapCreateSchema,
    BootstrapStatusOut,
    LoginOut,
    LoginSchema,
    PasswordUpdateSchema,
    ProfileUpdateSchema,
    UserOut,
)
from app.core.bootstrap import (
    bootstrap_status,
    create_super_admin,
    verify_bootstrap_code,
)
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository as repo
from app.services.security import hash_password, verify_password
from app.services.tournament_service import tournament_service

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

_PHONE_RE = re.compile(r"^1\d{10}$")


@auth_router.post("/login", response_model=LoginOut)
async def login(payload: LoginSchema):
    """手机号登录：已注册直接登录，未注册自动创建选手账号。"""
    return await tournament_service.login(payload.phone, payload.password)


@auth_router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    """当前登录用户信息（需登录）。"""
    return UserOut(
        id=user.id,
        nickname=user.nickname,
        phone=user.phone,
        role=user.role,
        created_at=user.created_at,
    )


@auth_router.patch("/profile", response_model=UserOut)
async def update_profile(payload: ProfileUpdateSchema, user: CurrentUser):
    """修改昵称（所有登录用户）。"""
    nickname = payload.nickname.strip()
    if not nickname:
        raise HTTPException(status_code=400, detail="昵称不能为空")
    updated = await repo.update_user_nickname(user.id, nickname)
    return UserOut(
        id=updated.id,
        nickname=updated.nickname,
        phone=updated.phone,
        role=updated.role,
        created_at=updated.created_at,
    )


@auth_router.patch("/password")
async def update_password(payload: PasswordUpdateSchema, user: CurrentUser):
    """修改密码：校验旧密码后更新（所有登录用户）。"""
    if user.password_hash is None:
        raise HTTPException(status_code=400, detail="当前账号未设置密码，无法修改")
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    await repo.update_user_password(user.id, hash_password(payload.new_password))
    return {"ok": True}


@auth_router.delete("/account")
async def delete_account(user: CurrentUser):
    """注销账号（软注销）：账号不可再登录，历史赛事与报名数据保留。"""
    await repo.soft_delete_user(user.id)
    return {"ok": True}


@auth_router.get("/bootstrap/status", response_model=BootstrapStatusOut)
async def bootstrap_status_endpoint():
    """系统无超管时返回 need_bootstrap=true 与一次性初始化码。"""
    return await bootstrap_status(repo)


@auth_router.post("/bootstrap", response_model=LoginOut)
async def bootstrap_create(payload: BootstrapCreateSchema):
    """凭一次性初始化码创建系统超级管理员（幂等，已有超管后关闭），成功后直接返回登录态。"""
    if not _PHONE_RE.match(payload.phone):
        raise HTTPException(status_code=400, detail="请输入有效的 11 位手机号")
    if not verify_bootstrap_code(payload.code):
        raise HTTPException(status_code=400, detail="初始化码不正确或已失效")
    nickname = f"管理员{payload.phone[-4:]}"
    user = await create_super_admin(
        repo, nickname=nickname, phone=payload.phone, password_hash=hash_password(payload.password)
    )
    from app.core.security import create_token

    return LoginOut(
        token=create_token(user.id),
        user=UserOut(
            id=user.id,
            nickname=user.nickname,
            phone=user.phone,
            role=user.role,
            created_at=user.created_at,
        ),
    )
