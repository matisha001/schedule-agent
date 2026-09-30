"""
SQL 校验节点

负责在真正执行查询前，用数据库解析一次生成的 SQL
校验结果不在这里决定流程走向，而是通过 state["error"] 交给 graph.py 的条件边判断
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


async def validate_sql(
    state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]
):
    """校验 SQL，并返回 error 字段控制后续条件分支"""

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

        try:
            # validate 内部使用 explain <sql>，只关心数据库能否成功解析这条 SQL
            await dw_mysql_repository.validate(sql)
            writer({"type": "progress", "step": step, "status": "success"})
            logger.info("SQL语法正确")
            return {"error": None}
        except Exception as e:
            # 不抛出异常中断图执行，而是把错误写入状态，供条件分支进入 correct_sql
            logger.info(f"SQL语法错误：{str(e)}")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"error": str(e)}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
