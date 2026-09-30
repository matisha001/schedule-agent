"""赛程/对局接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    phase_id: int | None = Field(default=None, description="所属阶段 ID")
    round: int = Field(default=1, ge=1, description="轮次序号（从 1 开始）")
    round_name: str | None = Field(default=None, max_length=32, description="轮次名称（如 八强赛）")
    bo: int = Field(default=1, ge=1, le=9, description="赛制 BO 数（1/3/5/7/9）")
    is_final: bool = Field(default=False, description="是否为决赛")
    home_team_id: int | None = Field(default=None, description="主队队伍 ID")
    away_team_id: int | None = Field(default=None, description="客队队伍 ID")
    start_time: datetime | None = Field(default=None, description="开赛时间")


class ScheduleUpdate(BaseModel):
    phase_id: int | None = Field(default=None, description="所属阶段 ID")
    round: int | None = Field(default=None, ge=1, description="轮次序号（从 1 开始）")
    round_name: str | None = Field(default=None, max_length=32, description="轮次名称（如 八强赛）")
    bo: int | None = Field(default=None, ge=1, le=9, description="赛制 BO 数（1/3/5/7/9）")
    is_final: bool | None = Field(default=None, description="是否为决赛")
    home_team_id: int | None = Field(default=None, description="主队队伍 ID")
    away_team_id: int | None = Field(default=None, description="客队队伍 ID")
    home_score: int | None = Field(default=None, ge=0, description="主队得分")
    away_score: int | None = Field(default=None, ge=0, description="客队得分")
    start_time: datetime | None = Field(default=None, description="开赛时间")
    status: int | None = Field(default=None, ge=0, le=3, description="0未开赛 1进行中 2已结束 3已取消")
