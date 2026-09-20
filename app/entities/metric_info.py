"""纯业务实体：指标信息。

描述赛事分析中可计算的指标（胜率、场均得分、净胜球等），
LLM 据此将自然语言指标映射为 SQL 聚合/计算表达式。
"""

from dataclasses import dataclass


@dataclass
class MetricInfo:
    id: str
    name: str
    agg_type: str  # count / sum / avg / max / min / custom
    expression: str  # 可直接拼入 SQL 的表达式
    description: str
    alias: list[str]
    table_id: str
