"""MetricInfo 双向转换器。"""

from dataclasses import asdict

from app.entities.metric_info import MetricInfo
from app.models.metric_info import MetricInfoMySQL


class MetricInfoMapper:
    @staticmethod
    def to_entity(model: MetricInfoMySQL) -> MetricInfo:
        return MetricInfo(
            id=model.id, name=model.name, agg_type=model.agg_type,
            expression=model.expression, description=model.description,
            alias=model.alias, table_id=model.table_id,
        )

    @staticmethod
    def to_model(entity: MetricInfo) -> MetricInfoMySQL:
        return MetricInfoMySQL(**asdict(entity))
