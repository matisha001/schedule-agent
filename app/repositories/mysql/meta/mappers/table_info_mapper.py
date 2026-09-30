"""TableInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    @staticmethod
    def to_entity(model: TableInfoMySQL) -> TableInfo:
        return TableInfo(
            id=model.id,
            name=model.name,
            role=model.role,
            description=model.description,
        )

    @staticmethod
    def to_model(entity: TableInfo) -> TableInfoMySQL:
        return TableInfoMySQL(**asdict(entity))
