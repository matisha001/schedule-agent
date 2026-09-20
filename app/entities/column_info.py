"""纯业务实体：字段元数据。

描述 meta 库中一张表的一个字段，供 LLM 生成 SQL 时理解字段语义。
"""

from dataclasses import dataclass


@dataclass
class ColumnInfo:
    id: str
    name: str
    type: str
    role: str  # dimension / measure / date / pk / fk
    examples: list
    description: str
    alias: list[str]
    table_id: str
