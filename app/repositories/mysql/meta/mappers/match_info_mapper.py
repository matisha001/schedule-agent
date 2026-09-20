"""MatchInfo 双向转换器（dw 库事实表）。"""

from dataclasses import asdict

from app.entities.match_info import MatchInfo
from app.models.match_info import MatchInfoMySQL


class MatchInfoMapper:
    @staticmethod
    def to_entity(model: MatchInfoMySQL) -> MatchInfo:
        return MatchInfo(
            id=model.id, tournament_id=model.tournament_id, round_name=model.round_name,
            home_team_id=model.home_team_id, away_team_id=model.away_team_id,
            match_time=model.match_time, venue=model.venue,
            home_score=model.home_score, away_score=model.away_score, status=model.status,
        )

    @staticmethod
    def to_model(entity: MatchInfo) -> MatchInfoMySQL:
        return MatchInfoMySQL(**asdict(entity))
