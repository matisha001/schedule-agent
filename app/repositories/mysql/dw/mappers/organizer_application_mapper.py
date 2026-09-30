"""OrganizerApplication 双向转换器。"""

from dataclasses import asdict

from app.entities.organizer_application_info import OrganizerApplicationInfo
from app.models.organizer_application_info import OrganizerApplicationMySQL


class OrganizerApplicationMapper:
    @staticmethod
    def to_entity(model: OrganizerApplicationMySQL) -> OrganizerApplicationInfo:
        return OrganizerApplicationInfo(
            id=model.id,
            user_id=model.user_id,
            status=model.status,
            reason=model.reason,
            reviewed_by=model.reviewed_by,
            reviewed_at=model.reviewed_at,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: OrganizerApplicationInfo) -> OrganizerApplicationMySQL:
        return OrganizerApplicationMySQL(**asdict(entity))
