"""meta_config.yaml 的程序内配置结构 + 加载（对应 docs/ag.md 8.3 配置格式）。

- 结构：MetaConfig → tables[TableConfig → columns[ColumnConfig]] + metrics[MetricConfig]
- 加载：OmegaConf 校验后转 dataclass，供 MetaKnowledgeService 使用
"""

from dataclasses import dataclass, field

from omegaconf import OmegaConf


@dataclass
class ColumnConfig:
    name: str  # 字段名（必须与 DW 中实际字段名一致）
    role: str = "dimension"  # primary_key / foreign_key / dimension / measure / date
    description: str = ""  # 字段业务说明（用于向量化语义入口）
    alias: list[str] = field(default_factory=list)  # 别名（每个别名都是独立的语义入口）
    sync: bool = False  # 是否同步真实取值到 ES/示例值（维度字段 true，主键/度量 false）


@dataclass
class TableConfig:
    name: str  # 表名（必须与 DW 中实际表名一致）
    role: str = "dim"  # dim（维度表）/ fact（事实表）
    description: str = ""  # 表业务说明
    columns: list[ColumnConfig] = field(default_factory=list)


@dataclass
class MetricConfig:
    name: str  # 指标名
    agg_type: str = "count"  # count / sum / avg / max / min / custom
    expression: str = ""  # 可拼入 SQL 的表达式
    description: str = ""  # 指标说明
    alias: list[str] = field(default_factory=list)  # 指标别名
    table_id: str = ""  # 指标所属表


@dataclass
class MetaConfig:
    tables: list[TableConfig] = field(default_factory=list)
    metrics: list[MetricConfig] = field(default_factory=list)


def load_meta_config(path: str) -> MetaConfig:
    """从 conf/meta_config.yaml 加载配置（缺失字段用默认值补齐）。"""
    context = OmegaConf.load(path)
    schema = OmegaConf.structured(MetaConfig)
    merged = OmegaConf.merge(schema, context)
    return OmegaConf.to_object(merged)
