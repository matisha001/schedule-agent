"""纯业务实体：用户（V3 定稿 + role 角色 + deleted_at 软注销扩展）。"""

from dataclasses import dataclass


@dataclass
class AppUserInfo:
    nickname: str
    guid: int | None = None
    phone: str | None = None
    password_hash: str | None = None
    role: str = "player"
    id: int | None = None
    created_at: str | None = None
    deleted_at: str | None = None
