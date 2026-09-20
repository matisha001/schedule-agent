"""TeamInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.team_info import TeamInfo
from app.models.team_info import TeamInfoMySQL


class TeamInfoMapper:
    @staticmethod
    def to_entity(model: TeamInfoMySQL) -> TeamInfo:
        return TeamInfo(
            id=model.id, name=model.name, sport=model.sport, short_name=model.short_name,
            region=model.region, home_venue=model.home_venue, description=model.description,
        )

    @staticmethod
    def to_model(entity: TeamInfo) -> TeamInfoMySQL:
        return TeamInfoMySQL(**asdict(entity))
