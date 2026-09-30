"""赛事 / 阶段接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="赛事名称")
    game: str | None = Field(default=None, max_length=64, description="比赛项目（如 王者荣耀）")
    game_maps: str | None = Field(default=None, max_length=2000, description="比赛地图/赛制说明")
    team_mode: int = Field(default=1, ge=1, le=2, description="1团队赛 2个人赛")
    start_time: datetime | None = Field(default=None, description="赛事开始时间")
    end_time: datetime | None = Field(default=None, description="赛事结束时间")
    reg_start_time: datetime | None = Field(default=None, description="报名开始时间")
    reg_end_time: datetime | None = Field(default=None, description="报名结束时间")
    max_team_members: int = Field(default=5, ge=1, le=50, description="每队最多成员数")
    max_teams: int = Field(default=16, ge=1, le=4096, description="最多队伍数")
    regist_method: int = Field(default=1, ge=1, le=2, description="1办赛者代报名 2选手自主报名")
    contact_requirement: str | None = Field(default=None, max_length=255, description="报名联系方式要求")
    rule_info: str | None = Field(default=None, max_length=2000, description="赛事规则说明")


class TournamentUpdate(TournamentCreate):
    pass


class PhaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32, description="阶段名称（如 小组赛）")
    start_time: datetime | None = Field(default=None, description="阶段开始时间")
    end_time: datetime | None = Field(default=None, description="阶段结束时间")


class PhaseUpdate(PhaseCreate):
    status: int | None = Field(default=None, ge=0, le=2, description="0未开始 1进行中 2已结束")


class TransitionAction(BaseModel):
    action: str = Field(
        description="publish(发布) / open(开始报名) / close(结束报名) / start(开始比赛) / finish(结束比赛)"
    )
