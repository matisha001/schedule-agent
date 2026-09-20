"""纯业务实体：比赛/赛程信息（dw 库核心事实表）。

初始设计，字段待用户后续补充确认（主客队、比分、进行状态等）。
"""

from dataclasses import dataclass


@dataclass
class MatchInfo:
    id: str
    tournament_id: str
    round_name: str  # 轮次/阶段：小组赛、1/4决赛...
    home_team_id: str
    away_team_id: str
    match_time: str  # ISO 时间
    venue: str
    home_score: int | None
    away_score: int | None
    status: str  # scheduled / live / finished / cancelled
