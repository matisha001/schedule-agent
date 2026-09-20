"""TournamentInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.tournament_info import TournamentInfo
from app.models.tournament_info import TournamentInfoMySQL


class TournamentInfoMapper:
    @staticmethod
    def to_entity(model: TournamentInfoMySQL) -> TournamentInfo:
        return TournamentInfo(
            id=model.id, name=model.name, sport=model.sport, season=model.season,
            level=model.level, status=model.status,
            start_date=model.start_date, end_date=model.end_date,
            description=model.description,
        )

    @staticmethod
    def to_model(entity: TournamentInfo) -> TournamentInfoMySQL:
        return TournamentInfoMySQL(**asdict(entity))
