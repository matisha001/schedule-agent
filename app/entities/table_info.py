"""纯业务实体：表元数据。

描述 meta 库中的一张业务表（名称/角色/描述），供 merge_retrieved_info
节点组装表结构上下文时补全描述信息。
"""

from dataclasses import dataclass


@dataclass
class TableInfo:
    id: str  # 表名（即 column_info.table_id）
    name: str  # 展示名（一般为表名）
    role: str  # dim（维度表）/ fact（事实表）
    description: str  # 表业务说明
