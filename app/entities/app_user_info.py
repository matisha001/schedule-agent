"""纯业务实体：用户（V3 定稿）。"""

from dataclasses import dataclass


@dataclass
class AppUserInfo:
    nickname: str
    guid: int | None = None
    phone: str | None = None
    id: int | None = None
    created_at: str | None = None
