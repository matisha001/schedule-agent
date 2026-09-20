"""DWMySQLRepository：执行赛事数据仓库查询。

只负责执行校验后的只读 SQL 并返回行数据。
"""

from sqlalchemy import text

from app.clients.mysql_client_manager import dw_mysql_client_manager


class DWMySQLRepository:
    async def run_select(self, sql: str) -> tuple[list[str], list[dict]]:
        """执行只读 SQL，返回 (列名, 行列表)。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return columns, [dict(zip(columns, row)) for row in rows]


dw_mysql_repository = DWMySQLRepository()
