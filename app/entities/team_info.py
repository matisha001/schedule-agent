"""纯业务实体：报名队伍（V3 定稿）。"""

from dataclasses import dataclass


@dataclass
class TeamInfo:
    tournament_id: int
    name: str
    status: int = 0  # 0待审核 1已确认 2已驳回 3已取消
    id: int | None = None
    created_at: str | None = None
