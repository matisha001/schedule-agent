"""纯业务实体：取值字典。

存放字段的常见取值（球队名、赛事名、赛制等），由 ES 提供模糊/分词检索，
用于把用户口语中的实体名解析为库内标准值。
"""

from dataclasses import dataclass


@dataclass
class ValueInfo:
    id: str
    field_name: str
    value: str
    aliases: list[str]
    description: str
