"""认证接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginSchema(BaseModel):
    phone: str = Field(min_length=11, max_length=11, description="11 位手机号")


class UserOut(BaseModel):
    id: int
    nickname: str
    phone: str | None = None
    created_at: datetime | None = None


class LoginOut(BaseModel):
    token: str
    user: UserOut
