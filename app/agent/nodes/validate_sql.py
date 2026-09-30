"""
SQL 校验节点

负责在真正执行查询前，用数据库解析一次生成的 SQL，
并执行问数权限防线③（docs/permission-design.md 第 5 节）的确定性终检：

- 禁止列：app_user.password_hash 等出现即拒绝（所有角色）
- 表集合：guest 的 deny_tables（player/app_user）完全不可见；非超管表必须 ⊆ 角色白名单
- 敏感列仅本人：非超管 SQL 引用 phone/guid 时必须含 app_user.id = 当前用户
- 行级范围：published 必须含 status >= 1；organizer 涉明细必须含 tournament.created_by = 当前用户

权限类错误一票否决（permission_blocked 直接结束，不交给 correct_sql 修正绕过）；
语法类错误维持原逻辑交给 correct_sql 修正。
"""

import re

from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.state import TournamentAgentState
from app.core.log import logger
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository

# 程序侧只读防线：仅放行 SELECT / WITH 开头的单条只读语句，拦截写操作和多语句注入
_READ_ONLY_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_MULTI_STMT_RE = re.compile(r";\s*\S")
# FROM/JOIN 后的表名（支持反引号包裹，统一小写去重）
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([`\w]+)", re.IGNORECASE)
# 明细表集合：organizer 查询这些表时必须 JOIN 赛事表并限定 created_by = 当前用户
_DETAIL_TABLES = {"player", "team", "schedule", "app_user"}


def extract_tables(sql: str) -> set[str]:
    return {t.strip("`").lower() for t in _TABLE_RE.findall(sql)}


def _has_status_ge_1(sql: str) -> bool:
    """SQL 中存在 status 约束且允许的数值 >= 1（status >= 1 / = 2 / IN (1,2,3) 等）。"""
    for op, val in re.findall(
        r"(?:tournament\.)?status\s*(>=|>|=)\s*(\d+)", sql, re.IGNORECASE
    ):
        n = int(val)
        if op == "=" and n >= 1:
            return True
        if op == ">=" and n >= 1:
            return True
        if op == ">" and n >= 0:
            return True
    for m in re.finditer(
        r"(?:tournament\.)?status\s*IN\s*\(([^)]*)\)", sql, re.IGNORECASE
    ):
        if any(int(x) >= 1 for x in re.findall(r"\d+", m.group(1))):
            return True
    return False


def check_permission(sql: str, context: dict) -> str | None:
    """确定性权限终检，返回错误信息（None = 通过）。

    注意：任何返回都会阻止 SQL 执行；权限类错误不允许走 LLM 修正绕过。
    """
    role = context.get("role", "guest")
    user_id = context.get("user_id")
    tables = extract_tables(sql)
    forbid_columns: set[str] = context.get("forbid_columns") or set()
    sensitive_columns: set[str] = context.get("sensitive_columns") or set()
    deny_tables: set[str] = context.get("deny_tables") or set()
    allowed_tables: set[str] = context.get("allowed_tables") or set()
    row_scope: str = context.get("row_scope", "all")

    # 1. 禁止列（所有角色，防御性兜底）
    for fc in forbid_columns:
        if re.search(rf"\b{fc.split('.')[-1]}\b", sql, re.IGNORECASE):
            return f"禁止使用敏感字段 {fc}，请移除后再查询"

    # 2. 完全不可见表（guest 的 player/app_user）
    for t in tables:
        if t in deny_tables:
            return f"当前角色无权查询 {t} 表数据"

    # 3. 表白名单（非超管）
    if role != "super_admin" and allowed_tables:
        for t in tables:
            if t not in allowed_tables:
                return (
                    f"当前角色无权查询 {t} 表，仅允许查询："
                    + "、".join(sorted(allowed_tables))
                )

    # 4. 敏感列仅本人（非超管）
    if role != "super_admin":
        for sc in sensitive_columns:
            if not re.search(rf"\b{sc.split('.')[-1]}\b", sql, re.IGNORECASE):
                continue
            if user_id is None:
                return f"敏感字段 {sc} 仅允许登录用户查询本人数据"
            if not re.search(
                rf"(?:app_user\.)?id\s*=\s*{user_id}\b", sql, re.IGNORECASE
            ):
                return (
                    f"敏感字段 {sc} 仅允许查询本人数据，"
                    f"请添加条件 app_user.id = {user_id}"
                )

    # 5. 行级范围
    if row_scope == "published":
        if "tournament" in tables and not _has_status_ge_1(sql):
            return "当前角色仅可查询已发布赛事，请添加条件 tournament.status >= 1"
    elif row_scope == "own_plus_published":
        if tables & _DETAIL_TABLES:
            # 涉队伍/选手/对局/用户明细：必须 JOIN 赛事表并限定自己创办的赛事
            if user_id is None:
                return "办赛者查询明细数据需要登录"
            if "tournament" not in tables:
                return (
                    f"办赛者查询队伍/选手/对局/用户明细必须 JOIN 赛事表，"
                    f"并添加条件 tournament.created_by = {user_id}"
                )
            if not re.search(
                rf"(?:tournament\.)?created_by\s*=\s*{user_id}\b",
                sql,
                re.IGNORECASE,
            ):
                return (
                    f"办赛者仅可查询自己创办的赛事数据，"
                    f"请添加条件 tournament.created_by = {user_id}"
                )
        elif "tournament" in tables:
            # 仅涉赛事主表：需已发布或自己创办
            if user_id is not None and re.search(
                rf"(?:tournament\.)?created_by\s*=\s*{user_id}\b",
                sql,
                re.IGNORECASE,
            ):
                pass
            elif not _has_status_ge_1(sql):
                return (
                    f"办赛者查询赛事需限定已发布（tournament.status >= 1）"
                    f"或自己创办（tournament.created_by = {user_id}）"
                )

    return None


async def validate_sql(
    state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]
):
    """校验 SQL（语法 + 权限终检），并返回 error 字段控制后续条件分支"""

    writer = runtime.stream_writer
    step = "校验SQL"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 读取 generate_sql 或 correct_sql 写入状态的候选 SQL
        sql = state["sql"]

        # SQL 可用性必须交给真实数仓判断，这里从运行时上下文取 DW Repository
        dw_mysql_repository: DWMySQLRepository = runtime.context[
            "dw_mysql_repository"
        ]

        # 只读防线：LLM 生成的 SQL 只允许是 SELECT/WITH 开头的单条只读语句
        if not sql or not _READ_ONLY_RE.match(sql):
            logger.info("SQL语法错误：仅允许 SELECT/WITH 只读查询")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"error": "仅允许 SELECT/WITH 只读查询"}
        if _MULTI_STMT_RE.search(sql):
            logger.info("SQL语法错误：不允许执行多条语句")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"error": "不允许执行多条语句"}

        # 权限防线③：确定性终检（权限错误一票否决，不进入 correct_sql 修正绕过）
        perm_error = check_permission(sql, dict(runtime.context))
        if perm_error:
            logger.info(f"权限校验未通过：{perm_error}")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"error": perm_error, "permission_blocked": True}

        try:
            # validate 内部使用 explain <sql>，只关心数据库能否成功解析这条 SQL
            await dw_mysql_repository.validate(sql)
            writer({"type": "progress", "step": step, "status": "success"})
            logger.info("SQL语法正确")
            return {"error": None, "permission_blocked": False}
        except Exception as e:
            # 不抛出异常中断图执行，而是把错误写入状态，供条件分支进入 correct_sql
            logger.info(f"SQL语法错误：{str(e)}")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"error": str(e), "permission_blocked": False}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
