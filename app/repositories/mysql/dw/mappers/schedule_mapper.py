"""Schedule 双向转换器。"""

from dataclasses import asdict

from app.entities.schedule_info import ScheduleInfo
from app.models.schedule_info import ScheduleInfoMySQL


class ScheduleMapper:
    @staticmethod
    def to_entity(model: ScheduleInfoMySQL) -> ScheduleInfo:
        return ScheduleInfo(
            id=model.id,
            tournament_id=model.tournament_id,
            phase_id=model.phase_id,
            round=model.round,
            round_name=model.round_name,
            bo=model.bo,
            is_final=model.is_final,
            home_team_id=model.home_team_id,
            away_team_id=model.away_team_id,
            home_score=model.home_score,
            away_score=model.away_score,
            status=model.status,
            start_time=model.start_time,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(entity: ScheduleInfo) -> ScheduleInfoMySQL:
        return ScheduleInfoMySQL(**asdict(entity))
