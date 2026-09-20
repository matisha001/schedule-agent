"""纯业务实体：赛事信息。

初始设计，字段待用户后续补充确认（赛制、奖金、分级、主办方等）。
"""

from dataclasses import dataclass


@dataclass
class TournamentInfo:
    id: str
    name: str
    sport: str  # 运动项目：足球/篮球/电竞...
    season: str  # 赛季：2025-2026
    level: str  # 级别：联赛/杯赛/资格赛
    status: str  # 状态：未开始/进行中/已结束
    start_date: str
    end_date: str
    description: str
