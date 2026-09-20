"""纯业务实体：赛程/对局（V3 定稿）。"""

from dataclasses import dataclass


@dataclass
class ScheduleInfo:
    tournament_id: int
    phase_id: int
    round: int = 1
    round_name: str | None = None
    bo: int = 1  # BO 局数
    is_final: int = 0
    home_team_id: int | None = None
    away_team_id: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    status: int = 0  # 0未开赛 1进行中 2已结束 3已取消
    start_time: str | None = None
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
