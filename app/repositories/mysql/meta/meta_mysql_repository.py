"""MetaMySQLRepository：读取 meta 库中的元数据（表结构、字典）。

骨架实现：提供按 table_id 查询字段元数据的接口。
依赖连接池初始化由 lifespan 完成。
"""

from sqlalchemy import select

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper


class MetaMySQLRepository:
    async def list_columns_by_table(self, table_id: str) -> list[ColumnInfo]:
        """按表查字段元数据。"""
        async with meta_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(ColumnInfoMySQL).where(ColumnInfoMySQL.table_id == table_id)
            )
            rows = result.scalars().all()
            return [ColumnInfoMapper.to_entity(row) for row in rows]

    async def list_all_columns(self) -> list[ColumnInfo]:
        """拉取全部字段元数据（用于构造建库/向量化）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            result = await session.execute(select(ColumnInfoMySQL))
            rows = result.scalars().all()
            return [ColumnInfoMapper.to_entity(row) for row in rows]


meta_mysql_repository = MetaMySQLRepository()
