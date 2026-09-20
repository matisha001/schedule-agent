"""Player 双向转换器。"""

from dataclasses import asdict

from app.entities.player_info import PlayerInfo
from app.models.player_info import PlayerInfoMySQL


class PlayerMapper:
    @staticmethod
    def to_entity(model: PlayerInfoMySQL) -> PlayerInfo:
        return PlayerInfo(
            id=model.id,
            team_id=model.team_id,
            nickname=model.nickname,
            user_id=model.user_id,
            is_captain=model.is_captain,
            status=model.status,
            player_type=model.player_type,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: PlayerInfo) -> PlayerInfoMySQL:
        return PlayerInfoMySQL(**asdict(entity))
