"""认证与用户管理接口 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginSchema(BaseModel):
    phone: str = Field(min_length=11, max_length=11, description="11 位手机号")
    password: str = Field(min_length=6, max_length=64, description="密码（6-64 位）")


class UserOut(BaseModel):
    id: int = Field(description="用户 ID")
    nickname: str = Field(description="用户昵称")
    phone: str | None = Field(default=None, description="手机号（11 位）")
    role: str = Field(default="player", description="角色：player(选手)/organizer(办赛者)/operator(运营)/super_admin(超管)")
    created_at: datetime | None = Field(default=None, description="创建时间")


class LoginOut(BaseModel):
    token: str = Field(description="登录令牌，后续请求以 Authorization: Bearer <token> 携带")
    user: UserOut = Field(description="登录用户信息")


class BootstrapStatusOut(BaseModel):
    need_bootstrap: bool = Field(description="系统是否需要初始化超管")
    code: str | None = Field(default=None, description="一次性初始化码（6 位）")


class BootstrapCreateSchema(BaseModel):
    code: str = Field(min_length=6, max_length=6, description="一次性初始化码")
    phone: str = Field(min_length=11, max_length=11, description="11 位手机号")
    password: str = Field(min_length=6, max_length=64, description="密码（6-64 位）")


# ---------- 用户管理（超管） ----------
class AdminUserOut(BaseModel):
    id: int = Field(description="用户 ID")
    nickname: str = Field(description="用户昵称")
    phone: str | None = Field(default=None, description="手机号（11 位）")
    role: str = Field(description="角色：player(选手)/organizer(办赛者)/operator(运营)/super_admin(超管)")
    created_at: datetime | None = Field(default=None, description="创建时间")


class AdminUserListOut(BaseModel):
    total: int = Field(description="用户总数")
    page: int = Field(default=1, description="当前页码（从 1 开始）")
    size: int = Field(default=20, description="每页数量")
    items: list[AdminUserOut] = Field(description="本页用户列表")


class UpdateRoleSchema(BaseModel):
    role: str = Field(pattern=r"^(player|organizer|operator|super_admin)$", description="目标角色")


# ---------- 账号资料 / 注销 ----------
class ProfileUpdateSchema(BaseModel):
    nickname: str = Field(min_length=1, max_length=64, description="新昵称")


class PasswordUpdateSchema(BaseModel):
    old_password: str = Field(min_length=6, max_length=64, description="当前密码")
    new_password: str = Field(min_length=6, max_length=64, description="新密码（6-64 位）")


# ---------- 办赛申请（玩家 → 办赛者） ----------
class OrganizerApplicationOut(BaseModel):
    id: int = Field(description="申请 ID")
    user_id: int = Field(description="申请人 ID")
    nickname: str = Field(default="", description="申请人昵称")
    status: str = Field(description="PENDING/APPROVED/REJECTED")
    reason: str | None = Field(default=None, description="申请说明")
    reviewed_by: int | None = Field(default=None, description="审批人 ID")
    reviewed_at: datetime | None = Field(default=None, description="审批时间")
    created_at: datetime | None = Field(default=None, description="申请时间")


class ApplicationCreateSchema(BaseModel):
    reason: str | None = Field(default=None, max_length=255, description="申请说明")


class ApplicationReviewSchema(BaseModel):
    approve: bool = Field(description="true=通过(升级为办赛者) / false=驳回")


class ApplicationListOut(BaseModel):
    total: int = Field(description="申请总数")
    page: int = Field(default=1, description="当前页码")
    size: int = Field(default=20, description="每页数量")
    items: list[OrganizerApplicationOut] = Field(description="本页申请列表")
