"""问数权限上下文（docs/permission-design.md 第 3/4/5 节）。

从 conf/app_config.yaml 的 query_permissions 段构建运行时权限：
- allowed_tables(role)：角色可见表集合（功能域 → 表）
- deny_tables(role)：完全不可见表集合（guest 的 player/app_user）
- row_scope(role)：行级范围（published / own_plus_published / all）
- sensitive_columns / forbid_columns：列级黑白名单
- row_scope_rules(role, user_id)：注入提示词的行级约束文本
"""

from app.conf.app_config import app_config

GUEST_ROLE = "guest"
ROLE_LABELS = {
    "guest": "游客（未登录）",
    "player": "玩家",
    "organizer": "办赛者",
    "operator": "运营",
    "super_admin": "系统超管",
}

# 业务表全集（validate_sql 表集合校验用）
KNOWN_TABLES = {"app_user", "tournament", "tournament_phase", "team", "player", "schedule"}


def _perms() -> dict:
    return app_config.query_permissions or {}


def allowed_tables(role: str) -> set[str]:
    """角色可见表集合（空表示不裁剪，兼容旧配置）。"""
    perms = _perms()
    role_conf = perms.get("roles", {}).get(role, {})
    domains = role_conf.get("domains", [])
    tables: set[str] = set()
    for domain in domains:
        tables.update(perms.get("domains", {}).get(domain, {}).get("tables", []))
    return tables


def deny_tables(role: str) -> set[str]:
    return set(_perms().get("roles", {}).get(role, {}).get("deny_tables", []))


def row_scope(role: str) -> str:
    return _perms().get("roles", {}).get(role, {}).get("row_scope", "all")


def sensitive_columns() -> set[str]:
    """敏感列（"表.列" 格式）：非超管引用时必须限定本人 app_user.id = uid。"""
    return set(_perms().get("sensitive_columns", []))


def forbid_columns() -> set[str]:
    """禁止列（"表.列" 格式）：任何 SQL 中出现即拒绝。"""
    return set(_perms().get("forbid_columns", []))


def is_super_admin(role: str) -> bool:
    return role == "super_admin"


def row_scope_rules(role: str, user_id: int | None) -> str:
    """生成注入 generate_sql / correct_sql 提示词的行级约束文本。"""
    scope = row_scope(role)
    lines: list[str] = []
    if scope == "published":
        lines.append("- 只能查询已发布的赛事数据：所有涉及赛事表的查询必须添加 `tournament.status >= 1` 条件")
    elif scope == "own_plus_published":
        lines.append("- 已发布的公开赛事数据可查询（涉及赛事表需加 `tournament.status >= 1`）")
        lines.append(
            f"- 查询队伍/选手/对局等明细时，只能查自己创办的赛事：必须 JOIN 赛事表并添加 `tournament.created_by = {user_id}` 条件"
        )
    if role != "super_admin":
        lines.append(
            f"- 手机号/guid 等敏感字段只能查询自己的记录：查询 app_user 表时必须添加 `app_user.id = {user_id}` 条件"
        )
    lines.append("- 严禁使用 app_user.password_hash 字段")
    return "\n".join(lines) if lines else "无额外行级限制"


def permission_prompt_section(role: str, user_id: int | None) -> str:
    """给 LLM 的完整权限约束段（generate_sql / correct_sql 用）。"""
    allowed = allowed_tables(role)
    scope = row_scope(role)
    table_desc = "、".join(sorted(allowed)) if allowed else "（未限制）"
    return (
        f"【权限约束（必须严格遵守）】\n"
        f"- 当前角色：{ROLE_LABELS.get(role, role)}（row_scope={scope}）\n"
        f"- 仅允许使用以下数据表：{table_desc}\n"
        f"{row_scope_rules(role, user_id)}"
    )
