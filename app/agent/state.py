"""LangGraph 状态定义：节点间流转的业务数据。"""

from typing import TypedDict

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class TournamentAgentState(TypedDict, total=False):
    query: str
    keywords: list[str]
    retrieved_column_infos: list[ColumnInfo]
    retrieved_metric_infos: list[MetricInfo]
    retrieved_value_infos: list[ValueInfo]
    table_infos: list[dict]  # 字段元数据按表聚合后的 schema 摘要
    metric_infos: list[dict]  # 指标摘要
    date_info: dict  # 时间条件解析结果（预留）
    db_info: dict  # 数据源信息（预留）
    sql: str
    error: str
    result: dict  # SQL 执行结果：{"columns": [...], "rows": [...]}
