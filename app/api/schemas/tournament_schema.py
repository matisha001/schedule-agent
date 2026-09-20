"""赛事 / 阶段接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    game: str | None = Field(default=None, max_length=64)
    game_maps: str | None = Field(default=None, max_length=2000)
    team_mode: int = Field(default=1, ge=1, le=2, description="1团队赛 2个人赛")
    start_time: datetime | None = None
    end_time: datetime | None = None
    reg_start_time: datetime | None = None
    reg_end_time: datetime | None = None
    max_team_members: int = Field(default=5, ge=1, le=50)
    max_teams: int = Field(default=16, ge=1, le=4096)
    regist_method: int = Field(default=1, ge=1, le=2, description="1办赛者代报名 2选手自主报名")
    contact_requirement: str | None = Field(default=None, max_length=255)
    rule_info: str | None = Field(default=None, max_length=2000)


class TournamentUpdate(TournamentCreate):
    pass


class PhaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    start_time: datetime | None = None
    end_time: datetime | None = None


class PhaseUpdate(PhaseCreate):
    status: int | None = Field(default=None, ge=0, le=2, description="0未开始 1进行中 2已结束")


class TransitionAction(BaseModel):
    action: str = Field(
        description="publish(发布) / open(开始报名) / close(结束报名) / start(开始比赛) / finish(结束比赛)"
    )
