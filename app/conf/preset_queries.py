"""预制提示词加载：读取 conf/preset_queries.yaml，按角色过滤（docs/permission-design.md 第 7 节）。

- 未登录 → guest；登录 → user.role
- 每种角色默认恰好 4 条（visible_to 精确指定），按 order 排序返回
"""

from pathlib import Path

import yaml

DEFAULT_CONF = Path(__file__).resolve().parents[2] / "conf" / "preset_queries.yaml"


def load_preset_queries(conf_path: Path = DEFAULT_CONF) -> list[dict]:
    data = yaml.safe_load(conf_path.read_text(encoding="utf-8"))
    return data.get("preset_queries", [])


def filter_by_role(role: str, presets: list[dict] | None = None) -> list[dict]:
    """按角色过滤并排序（未登录 role='guest'）。"""
    items = presets if presets is not None else load_preset_queries()
    matched = [p for p in items if role in (p.get("visible_to") or [])]
    matched.sort(key=lambda p: p.get("order", 0))
    return matched
