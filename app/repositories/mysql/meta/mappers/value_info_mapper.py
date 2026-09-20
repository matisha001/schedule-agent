"""ValueInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.value_info import ValueInfo
from app.models.value_info import ValueInfoMySQL


class ValueInfoMapper:
    @staticmethod
    def to_entity(model: ValueInfoMySQL) -> ValueInfo:
        return ValueInfo(
            id=model.id, field_name=model.field_name, value=model.value,
            aliases=model.aliases, description=model.description,
        )

    @staticmethod
    def to_model(entity: ValueInfo) -> ValueInfoMySQL:
        return ValueInfoMySQL(**asdict(entity))
