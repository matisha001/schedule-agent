"""Team 双向转换器。"""

from dataclasses import asdict

from app.entities.team_info import TeamInfo
from app.models.team_info import TeamInfoMySQL


class TeamMapper:
    @staticmethod
    def to_entity(model: TeamInfoMySQL) -> TeamInfo:
        return TeamInfo(
            id=model.id,
            tournament_id=model.tournament_id,
            name=model.name,
            status=model.status,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: TeamInfo) -> TeamInfoMySQL:
        return TeamInfoMySQL(**asdict(entity))
