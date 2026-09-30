"""报名（队伍/选手）接口 Schema。"""

from pydantic import BaseModel, Field


class PlayerPayload(BaseModel):
    nickname: str = Field(min_length=1, max_length=64, description="选手昵称")
    is_captain: bool = Field(default=False, description="是否队长")


class TeamCreate(BaseModel):
    name: str = Field(default="", max_length=64, description="队伍名（个人赛可空，自动取昵称）")
    players: list[PlayerPayload] = Field(default_factory=list, max_length=50, description="队伍成员列表（最多 50 人）")


class PlayerCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=64, description="选手昵称")
    is_captain: bool = Field(default=False, description="是否队长")


class TeamStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=3, description="0待审核 1已确认 2已驳回 3已取消")


class PlayerStatusUpdate(BaseModel):
    status: str = Field(description="AGREED / REJECTED")
