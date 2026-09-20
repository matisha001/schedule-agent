"""纯业务实体：选手（V3 定稿）。"""

from dataclasses import dataclass


@dataclass
class PlayerInfo:
    team_id: int
    nickname: str
    user_id: int | None = None  # TEMP 选手指虚拟 user id=1
    is_captain: int = 0
    status: str = "PENDING"  # AGREED/PENDING/REJECTED
    player_type: str = "TEMP"  # TEMP临时 REAL正式
    id: int | None = None
    created_at: str | None = None
