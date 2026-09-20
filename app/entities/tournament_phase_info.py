"""纯业务实体：赛事阶段（V3 定稿，仅基础信息）。"""

from dataclasses import dataclass


@dataclass
class TournamentPhaseInfo:
    tournament_id: int
    name: str
    start_time: str | None = None
    end_time: str | None = None
    status: int = 0  # 0未开始 1进行中 2已结束
    id: int | None = None
