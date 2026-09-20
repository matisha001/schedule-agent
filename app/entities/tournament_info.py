"""纯业务实体：赛事（V3 定稿，敏感信息不落库）。"""

from dataclasses import dataclass


@dataclass
class TournamentInfo:
    name: str
    created_by: int
    game: str | None = None
    game_maps: str | None = None  # 自由文本
    team_mode: int = 1  # 1团队赛 2个人赛
    start_time: str | None = None
    end_time: str | None = None
    reg_start_time: str | None = None
    reg_end_time: str | None = None
    max_team_members: int = 5
    max_teams: int = 16
    regist_method: int = 1  # 1办赛者代报名 2选手自主报名
    contact_requirement: str | None = None  # 自由文本
    rule_info: str | None = None  # 自由文本
    status: int = 0  # 0草稿 1已发布 2报名中 3比赛中 4已结束
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
