"""AppUser 双向转换器。"""

from dataclasses import asdict

from app.entities.app_user_info import AppUserInfo
from app.models.app_user_info import AppUserInfoMySQL


class AppUserMapper:
    @staticmethod
    def to_entity(model: AppUserInfoMySQL) -> AppUserInfo:
        return AppUserInfo(
            id=model.id,
            nickname=model.nickname,
            guid=model.guid,
            phone=model.phone,
            password_hash=model.password_hash,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: AppUserInfo) -> AppUserInfoMySQL:
        return AppUserInfoMySQL(**asdict(entity))
