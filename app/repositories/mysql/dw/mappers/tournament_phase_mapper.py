"""TournamentPhase 双向转换器。"""

from dataclasses import asdict

from app.entities.tournament_phase_info import TournamentPhaseInfo
from app.models.tournament_phase_info import TournamentPhaseInfoMySQL


class TournamentPhaseMapper:
    @staticmethod
    def to_entity(model: TournamentPhaseInfoMySQL) -> TournamentPhaseInfo:
        return TournamentPhaseInfo(
            id=model.id,
            tournament_id=model.tournament_id,
            name=model.name,
            start_time=model.start_time,
            end_time=model.end_time,
            status=model.status,
        )

    @staticmethod
    def to_model(entity: TournamentPhaseInfo) -> TournamentPhaseInfoMySQL:
        return TournamentPhaseInfoMySQL(**asdict(entity))
