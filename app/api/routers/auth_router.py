"""认证路由：手机号登录（不存在自动注册）。"""


from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.api.schemas.auth_schema import LoginOut, LoginSchema, UserOut
from app.services.tournament_service import tournament_service

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=LoginOut)
async def login(payload: LoginSchema):
    return await tournament_service.login(payload.phone, payload.password)


@auth_router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return UserOut(
        id=user.id,
        nickname=user.nickname,
        phone=user.phone,
        created_at=user.created_at,
    )
