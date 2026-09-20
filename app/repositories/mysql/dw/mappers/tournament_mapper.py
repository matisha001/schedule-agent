"""Tournament 双向转换器。"""

from dataclasses import asdict

from app.entities.tournament_info import TournamentInfo
from app.models.tournament_info import TournamentInfoMySQL


class TournamentMapper:
    @staticmethod
    def to_entity(model: TournamentInfoMySQL) -> TournamentInfo:
        return TournamentInfo(
            id=model.id,
            name=model.name,
            created_by=model.created_by,
            game=model.game,
            game_maps=model.game_maps,
            team_mode=model.team_mode,
            start_time=model.start_time,
            end_time=model.end_time,
            reg_start_time=model.reg_start_time,
            reg_end_time=model.reg_end_time,
            max_team_members=model.max_team_members,
            max_teams=model.max_teams,
            regist_method=model.regist_method,
            contact_requirement=model.contact_requirement,
            rule_info=model.rule_info,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: TournamentInfo) -> TournamentInfoMySQL:
        return TournamentInfoMySQL(**asdict(entity))
