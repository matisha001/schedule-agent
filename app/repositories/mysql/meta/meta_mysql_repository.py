"""MetaMySQLRepository：读写 meta 库中的元数据（表结构、字段、指标、取值字典）。

对应 docs/ag.md：
- 在线查询：merge_retrieved_info 节点用 get_column_info_by_id / get_key_columns_by_table_id /
  get_table_info_by_id 补齐字段、主外键和表描述；
- 离线构建：save_* 方法批量写入（幂等替换），list_all_* 读取全量数据供向量化/ES 索引。
依赖连接池初始化由 lifespan 完成。
"""

from sqlalchemy import delete, select, text

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.models.column_info import ColumnInfoMySQL
from app.models.metric_info import MetricInfoMySQL
from app.models.table_info import TableInfoMySQL
from app.models.value_info import ValueInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper
from app.repositories.mysql.meta.mappers.value_info_mapper import ValueInfoMapper


class MetaMySQLRepository:
    async def ensure_table_info(self) -> None:
        """确保 table_info 表存在（兼容 docker 首次初始化后新增的表）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(text(
                "CREATE TABLE IF NOT EXISTS table_info ("
                " id VARCHAR(64) NOT NULL COMMENT '主键（表名）',"
                " name VARCHAR(128) NOT NULL COMMENT '展示名',"
                " role VARCHAR(32) DEFAULT NULL COMMENT 'dim/fact',"
                " description TEXT DEFAULT NULL COMMENT '表业务说明',"
                " PRIMARY KEY (id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表元数据'"
            ))
            await session.commit()

    # ---------- 写入（离线构建，幂等替换整表） ----------

    async def save_table_infos(self, infos: list[TableInfo]) -> None:
        """整表替换 table_info（先清后插，同一事务）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(delete(TableInfoMySQL))
            session.add_all([TableInfoMapper.to_model(info) for info in infos])
            await session.commit()

    async def save_column_infos(self, infos: list[ColumnInfo]) -> None:
        """整表替换 column_info（先清后插，同一事务）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(delete(ColumnInfoMySQL))
            session.add_all([ColumnInfoMapper.to_model(info) for info in infos])
            await session.commit()

    async def save_metric_infos(self, infos: list[MetricInfo]) -> None:
        """整表替换 metric_info（先清后插，同一事务）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(delete(MetricInfoMySQL))
            session.add_all([MetricInfoMapper.to_model(info) for info in infos])
            await session.commit()

    async def save_value_infos(self, infos: list[ValueInfo]) -> None:
        """整表替换 value_info（先清后插，同一事务）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(delete(ValueInfoMySQL))
            session.add_all([ValueInfoMapper.to_model(info) for info in infos])
            await session.commit()

    # ---------- 读取（在线查询） ----------

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

    async def list_all_metrics(self) -> list[MetricInfo]:
        """拉取全部指标元数据（用于离线向量化构建）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            result = await session.execute(select(MetricInfoMySQL))
            rows = result.scalars().all()
            return [MetricInfoMapper.to_entity(row) for row in rows]

    async def list_all_values(self) -> list[ValueInfo]:
        """拉取全部取值字典（用于离线 ES 索引构建）。"""
        async with meta_mysql_client_manager.session_factory() as session:
            result = await session.execute(select(ValueInfoMySQL))
            rows = result.scalars().all()
            return [ValueInfoMapper.to_entity(row) for row in rows]

    async def get_column_info_by_id(self, id: str) -> ColumnInfo | None:
        """按字段 id 查字段元数据，供合并节点补齐字段上下文。"""
        async with meta_mysql_client_manager.session_factory() as session:
            row = await session.get(ColumnInfoMySQL, id)
            return ColumnInfoMapper.to_entity(row) if row else None

    async def get_table_info_by_id(self, id: str) -> TableInfo | None:
        """按表 id 查表元数据（描述/角色），供合并节点组装表结构上下文。"""
        async with meta_mysql_client_manager.session_factory() as session:
            row = await session.get(TableInfoMySQL, id)
            return TableInfoMapper.to_entity(row) if row else None

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        """查询指定表的主外键字段，避免 Join 关键字段被向量召回漏掉。"""
        async with meta_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM column_info "
                    "WHERE table_id = :table_id AND role IN ('pk', 'fk')"
                ),
                {"table_id": table_id},
            )
            return [ColumnInfo(**dict(row)) for row in result.mappings().fetchall()]


meta_mysql_repository = MetaMySQLRepository()
