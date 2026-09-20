"""ColumnInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL


class ColumnInfoMapper:
    @staticmethod
    def to_entity(model: ColumnInfoMySQL) -> ColumnInfo:
        return ColumnInfo(
            id=model.id, name=model.name, type=model.type,
            role=model.role, examples=model.examples,
            description=model.description, alias=model.alias,
            table_id=model.table_id,
        )

    @staticmethod
    def to_model(entity: ColumnInfo) -> ColumnInfoMySQL:
        return ColumnInfoMySQL(**asdict(entity))
