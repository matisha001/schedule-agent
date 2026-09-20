"""赛程/对局接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    phase_id: int | None = None
    round: int = Field(default=1, ge=1)
    round_name: str | None = Field(default=None, max_length=32)
    bo: int = Field(default=1, ge=1, le=9)
    is_final: bool = False
    home_team_id: int | None = None
    away_team_id: int | None = None
    start_time: datetime | None = None


class ScheduleUpdate(BaseModel):
    phase_id: int | None = None
    round: int | None = Field(default=None, ge=1)
    round_name: str | None = Field(default=None, max_length=32)
    bo: int | None = Field(default=None, ge=1, le=9)
    is_final: bool | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)
    start_time: datetime | None = None
    status: int | None = Field(default=None, ge=0, le=3, description="0未开赛 1进行中 2已结束 3已取消")
