"""超管首次启动引导创建（docs/permission-design.md 第 6 节）。

- 启动/查询时若 app_user 无 super_admin，生成一次性初始化码（打印日志 + status 接口返回）
- POST /api/auth/bootstrap 凭初始化码创建超管（事务内二次校验，幂等防抢注）
- 已有超管后初始化码失效，接口关闭
"""

import hmac
import secrets

from fastapi import HTTPException

from app.core.log import logger

SUPER_ADMIN_ROLE = "super_admin"
# 允许写入的角色全集（用户管理页可选值）
VALID_ROLES = {"player", "organizer", "operator", "super_admin"}

# 模块级一次性初始化码（lifespan/查询时惰性生成；已有超管后置空）
_bootstrap_code: str | None = None


def _ensure_code() -> str:
    global _bootstrap_code
    if _bootstrap_code is None:
        _bootstrap_code = "".join(secrets.choice("0123456789ABCDEF") for _ in range(6))
        logger.info(
            f"系统尚无超级管理员，初始化码：{_bootstrap_code}（仅首次部署使用，创建超管后失效）"
        )
    return _bootstrap_code


def reset_bootstrap_code() -> None:
    """已有超管后清空初始化码，关闭引导通道。"""
    global _bootstrap_code
    _bootstrap_code = None


async def bootstrap_status(repo) -> dict:
    """返回 {need_bootstrap, code}；无超管时附带一次性初始化码。"""
    count = await repo.count_users_by_role(SUPER_ADMIN_ROLE)
    if count > 0:
        return {"need_bootstrap": False, "code": None}
    return {"need_bootstrap": True, "code": _ensure_code()}


def verify_bootstrap_code(code: str) -> bool:
    if not _bootstrap_code:
        return False
    return hmac.compare_digest(code.strip().upper(), _bootstrap_code)


async def create_super_admin(repo, nickname: str, phone: str, password_hash: str):
    """凭初始化码创建超管：事务内二次校验仍无超管，幂等防抢注。"""
    if await repo.count_users_by_role(SUPER_ADMIN_ROLE) > 0:
        raise HTTPException(status_code=409, detail="系统已存在超级管理员，引导通道已关闭")
    user = await repo.create_user(nickname=nickname, phone=phone, password_hash=password_hash)
    # create_user 默认 role=player，这里提升为超管并清空初始化码
    updated = await repo.update_user_role(user.id, SUPER_ADMIN_ROLE)
    reset_bootstrap_code()
    return updated
