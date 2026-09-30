"""ValueInfo 双向转换器。

meta 库 aliases 列为 VARCHAR（逗号分隔或 JSON 数组字符串），
统一解析为 list[str] 供实体与 ES 写入使用。
"""

import json
from dataclasses import asdict

from app.entities.value_info import ValueInfo
from app.models.value_info import ValueInfoMySQL


def _parse_aliases(raw: str | list | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(a) for a in raw]
    text = str(raw).strip()
    if not text or text == "[]":
        return []
    if text.startswith("["):
        try:
            return [str(a) for a in json.loads(text)]
        except json.JSONDecodeError:
            return []
    return [a.strip() for a in text.split(",") if a.strip()]


def _serialize_aliases(aliases: list[str]) -> str:
    return json.dumps(aliases, ensure_ascii=False)


class ValueInfoMapper:
    @staticmethod
    def to_entity(model: ValueInfoMySQL) -> ValueInfo:
        return ValueInfo(
            id=model.id,
            field_name=model.field_name,
            value=model.value,
            aliases=_parse_aliases(model.aliases),
            description=model.description,
        )

    @staticmethod
    def to_model(entity: ValueInfo) -> ValueInfoMySQL:
        return ValueInfoMySQL(**{**asdict(entity), "aliases": _serialize_aliases(entity.aliases)})
