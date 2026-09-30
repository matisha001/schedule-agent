"""元数据知识库构建服务：组织"DW → meta MySQL → Qdrant/ES"的完整构建流程。

对应 docs/ag.md 第八节。分层约定：
- 本层只做业务编排与领域规则（角色推断、默认配置生成、指标定义、语义入口拆分、批量向量化）；
- 存储读写全部委托 repository（meta/dw MySQL、Qdrant、ES）；
- 实体↔ORM 转换由各 Mapper 完成；
- 表/字段/指标定义以 conf/meta_config.yaml 为唯一配置来源（8.3 格式），
  由 seed 脚本 --init 生成默认配置后允许人工修改。
"""

import asyncio
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from loguru import logger

from app.conf.meta_config import ColumnConfig, MetaConfig, MetricConfig, TableConfig
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

# 每批 Embedding 条数，减少 API 调用次数（docs/ag.md 8.2）
BATCH_SIZE = 20

# 参与知识库构建的 DW 业务表（默认配置）
BUILD_TABLES = ["app_user", "tournament", "tournament_phase", "team", "player", "schedule"]

# 表角色/描述（与 schema_dw.sql 建表注释一致，生成默认配置用）
_TABLE_ROLES: dict[str, tuple[str, str]] = {
    "app_user": ("dim", "用户基础信息（含系统虚拟用户）"),
    "tournament": ("dim", "赛事主表：名称、时间、报名与比赛规则"),
    "tournament_phase": ("dim", "赛事阶段：初赛/总决赛等"),
    "team": ("dim", "报名队伍（个人赛按单人队伍复用）"),
    "player": ("dim", "参赛选手"),
    "schedule": ("fact", "赛程/对局：对阵、比分、轮次与状态"),
}

# 度量字段白名单：虽为数值但属度量口径（用于 score/上限 等统计）
_MEASURE_COLUMNS: set[tuple[str, str]] = {
    ("schedule", "home_score"),
    ("schedule", "away_score"),
    ("tournament", "max_teams"),
    ("tournament", "max_team_members"),
}

# 默认指标定义（生成默认配置用）
_DEFAULT_METRICS: list[MetricConfig] = [
    MetricConfig(name="报名队伍数", agg_type="count", expression="COUNT(*)",
                 description="报名队伍数量。", alias=["队伍数", "参赛队伍数", "报名队数"], table_id="team"),
    MetricConfig(name="队伍人数", agg_type="count", expression="COUNT(*)",
                 description="参赛选手总人数。", alias=["选手人数", "参赛人数", "队员数"], table_id="player"),
    MetricConfig(name="赛事数量", agg_type="count", expression="COUNT(*)",
                 description="赛事总数。", alias=["比赛数量", "赛事总数"], table_id="tournament"),
    MetricConfig(name="对局数量", agg_type="count", expression="COUNT(*)",
                 description="赛程对局总数。", alias=["比赛场次", "对局数", "场次"], table_id="schedule"),
    MetricConfig(name="总得分", agg_type="sum", expression="SUM(home_score + away_score)",
                 description="所有对局双方得分总和。", alias=["总比分", "总得分和"], table_id="schedule"),
    MetricConfig(name="场均得分", agg_type="avg", expression="AVG(home_score + away_score)",
                 description="每场对局双方得分平均值。", alias=["平均得分", "场均分"], table_id="schedule"),
    MetricConfig(name="单场最高分", agg_type="max", expression="MAX(home_score + away_score)",
                 description="单场对局双方得分之和的最大值。", alias=["最高得分", "单场最高"], table_id="schedule"),
]

# 状态枚举（值+人类可读别名，作为取值字典的领域补充）
_ENUM_VALUES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("tournament", "status"): [("0", "草稿"), ("1", "已发布"), ("2", "报名中"), ("3", "比赛中"), ("4", "已结束")],
    ("team", "status"): [("0", "待审核"), ("1", "已确认"), ("2", "已驳回"), ("3", "已取消")],
    ("schedule", "status"): [("0", "未开赛"), ("1", "进行中"), ("2", "已结束"), ("3", "已取消")],
    ("player", "status"): [("AGREED", "已同意"), ("PENDING", "待确认"), ("REJECTED", "已拒绝")],
    ("player", "player_type"): [("TEMP", "临时选手"), ("REAL", "正式选手")],
}


def _type_length(column_type: str) -> int:
    """从 COLUMN_TYPE（如 varchar(64)）解析长度，无长度返回 0。"""
    match = re.search(r"\((\d+)\)", column_type)
    return int(match.group(1)) if match else 0


# cp1252 中 0x80-0x9F 特殊字符的反向映射（含 0x8F 等未定义槽位按 latin1 控制符处理）
_CP1252_REV = {
    0x20AC: 0x80, 0x201A: 0x82, 0x0192: 0x83, 0x201E: 0x84, 0x2026: 0x85,
    0x2020: 0x86, 0x2021: 0x87, 0x02C6: 0x88, 0x2030: 0x89, 0x0160: 0x8A,
    0x2039: 0x8B, 0x0152: 0x8C, 0x017D: 0x8E, 0x2018: 0x91, 0x2019: 0x92,
    0x201C: 0x93, 0x201D: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97,
    0x02DC: 0x98, 0x2122: 0x99, 0x0161: 0x9A, 0x203A: 0x9B, 0x0153: 0x9C,
    0x017E: 0x9E, 0x0178: 0x9F,
}


def _repair_mojibake(text: str) -> str:
    """修复 DW 注释的双重编码（docker 初始化时被 latin1/cp1252 误存，如 昵称 -> æ˜µç§°）。

    先按反向映射还原为原始 UTF-8 字节再解码；仅当结果合法 UTF-8 时生效，
    正常中文文本不会被误伤。
    """
    if not text:
        return text
    try:
        raw = bytearray()
        for c in text:
            cp = ord(c)
            if cp <= 0xFF:
                raw.append(cp)
            elif cp in _CP1252_REV:
                raw.append(_CP1252_REV[cp])
            else:
                return text
        return bytes(raw).decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return text


def _is_sampleable(schema_col: dict) -> bool:
    """是否适合抽样真实取值（短文本/枚举类字段，排除长文本噪音）。"""
    if schema_col["is_pk"] or schema_col["is_fk"] or schema_col["data_type"] in ("datetime", "timestamp", "date"):
        return False
    if (schema_col["table"], schema_col["column"]) in _MEASURE_COLUMNS:
        return False
    if schema_col["data_type"] not in ("varchar", "char", "tinyint", "int"):
        return False
    return not (schema_col["data_type"] in ("varchar", "char") and _type_length(schema_col["type"]) > 128)


def _role_for(table: str, column: str, is_pk: bool, is_fk: bool, data_type: str) -> str:
    if is_pk:
        return "pk"
    if is_fk:
        return "fk"
    if data_type in ("datetime", "timestamp", "date"):
        return "date"
    if (table, column) in _MEASURE_COLUMNS:
        return "measure"
    return "dimension"


def _semantic_entries(base_id: str, name: str, description: str, alias: list[str]) -> list[tuple[str, str]]:
    """把一条元数据拆成多个语义入口：(唯一 point id, 向量化文本)。

    base_id 必须是限定 id（如 schedule.created_at / metric.报名队伍数），
    否则不同表的重名字段（created_at/id/status）会生成相同 point id 互相覆盖。
    """
    entries = []
    if name:
        entries.append((f"{base_id}#name", name))
    if description and description != name:
        entries.append((f"{base_id}#desc", description))
    for i, a in enumerate(alias):
        if a and a != name:
            entries.append((f"{base_id}#alias{i}", a))
    return entries


@dataclass
class SeedStats:
    tables: int
    columns: int
    metrics: int
    values: int


class MetaKnowledgeService:
    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
        embedding_client,
    ):
        self.meta_repo = meta_mysql_repository
        self.dw_repo = dw_mysql_repository
        self.column_qdrant_repo = column_qdrant_repository
        self.metric_qdrant_repo = metric_qdrant_repository
        self.value_es_repo = value_es_repository
        self.embedding_client = embedding_client

    # ================= 步骤 A1：生成默认 conf/meta_config.yaml =================

    async def generate_config(self, path: str) -> MetaConfig:
        """从 DW 真实结构 + 领域规则生成默认 meta_config.yaml（供人工修改）。"""
        schema = await self.dw_repo.get_table_schema(BUILD_TABLES)

        tables: list[TableConfig] = []
        for table in BUILD_TABLES:
            role, desc = _TABLE_ROLES.get(table, ("dim", ""))
            columns = [
                ColumnConfig(
                    name=c["column"],
                    role=_role_for(table, c["column"], c["is_pk"], c["is_fk"], c["data_type"]),
                    description=_repair_mojibake(c["comment"]),
                    alias=[],
                    # 仅短文本/枚举类维度字段同步真实取值（主键/度量/长文本不同步）
                    sync=_is_sampleable(c) and _role_for(table, c["column"], c["is_pk"], c["is_fk"], c["data_type"]) == "dimension",
                )
                for c in schema
                if c["table"] == table
            ]
            tables.append(TableConfig(name=table, role=role, description=desc, columns=columns))

        config = MetaConfig(tables=tables, metrics=_DEFAULT_METRICS)
        # 配置生成属一次性管理操作，同步写文件避免引入异步 IO 复杂度
        yaml_text = yaml.dump(asdict(config), allow_unicode=True, sort_keys=False)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: Path(path).write_text(yaml_text, encoding="utf-8"))
        logger.info("已生成默认配置：{}（可手工修改后重新 seed）", path)
        return config

    # ================= 步骤 A2：DW → meta MySQL（按配置灌种子） =================

    async def seed_meta(self, config: MetaConfig) -> SeedStats:
        """按 conf/meta_config.yaml 从 DW 读取真实类型/取值，整表替换写入 meta 库。"""
        tables = [t.name for t in config.tables]
        schema = await self.dw_repo.get_table_schema(tables)
        schema_by_table = {t: [c for c in schema if c["table"] == t] for t in tables}

        table_infos = [
            TableInfo(id=t.name, name=t.name, role=t.role, description=t.description)
            for t in config.tables
        ]

        column_infos: list[ColumnInfo] = []
        for t in config.tables:
            real_by_name = {c["column"]: c for c in schema_by_table.get(t.name, [])}
            for col in t.columns:
                real = real_by_name.get(col.name)
                column_infos.append(ColumnInfo(
                    id=f"{t.name}.{col.name}", name=col.name,
                    type=real["type"] if real else "",
                    role=col.role,
                    examples=[],
                    description=col.description,
                    alias=col.alias,
                    table_id=t.name,
                ))

        # 为 sync:true 的字段补充真实示例值
        for t in config.tables:
            for col in t.columns:
                if not col.sync:
                    continue
                samples = await self.dw_repo.get_column_values(t.name, col.name)
                if samples:
                    target = next(x for x in column_infos if x.id == f"{t.name}.{col.name}")
                    target.examples = samples

        metric_infos = [
            MetricInfo(
                id=f"metric.{m.name}", name=m.name, agg_type=m.agg_type,
                expression=m.expression, description=m.description,
                alias=m.alias, table_id=m.table_id,
            )
            for m in config.metrics
        ]

        # 取值字典：sync 字段真实取值 + 状态枚举（枚举带人类可读别名，按 id 去重且枚举优先）
        value_by_id: dict[str, ValueInfo] = {}
        for t in config.tables:
            for col in t.columns:
                if not col.sync:
                    continue
                col_id = f"{t.name}.{col.name}"
                for value in await self.dw_repo.get_column_values(t.name, col.name):
                    if value:
                        value_by_id.setdefault(f"{col_id}.{value}",
                                               ValueInfo(id=f"{col_id}.{value}", field_name=col_id, value=value, aliases=[], description=""))
        for (table, column), pairs in _ENUM_VALUES.items():
            if table not in tables:
                continue
            col_id = f"{table}.{column}"
            for value, label in pairs:
                vid = f"{col_id}.{value}"
                value_by_id[vid] = ValueInfo(id=vid, field_name=col_id, value=value, aliases=[label], description="")
        value_infos = list(value_by_id.values())

        await self.meta_repo.ensure_table_info()
        await self.meta_repo.save_table_infos(table_infos)
        await self.meta_repo.save_column_infos(column_infos)
        await self.meta_repo.save_metric_infos(metric_infos)
        await self.meta_repo.save_value_infos(value_infos)

        stats = SeedStats(
            tables=len(table_infos), columns=len(column_infos),
            metrics=len(metric_infos), values=len(value_infos),
        )
        logger.info("meta 种子数据灌入完成：table_info={} 张，column_info={} 个，metric_info={} 个，value_info={} 条",
                    stats.tables, stats.columns, stats.metrics, stats.values)
        return stats

    # ================= 步骤 B：meta MySQL → Qdrant / ES（索引构建） =================

    async def build(self) -> None:
        """把 meta 库元数据向量化写入 Qdrant（字段/指标），取值写入 ES。"""
        size = self._embedding_size()
        await self.column_qdrant_repo.ensure_collection(size)
        await self.metric_qdrant_repo.ensure_collection(size)

        columns = await self.meta_repo.list_all_columns()
        if columns:
            await self._upsert_columns(columns)
        else:
            logger.warning("meta 库 column_info 为空，跳过字段向量化")

        metrics = await self.meta_repo.list_all_metrics()
        if metrics:
            await self._upsert_metrics(metrics)
        else:
            logger.warning("meta 库 metric_info 为空，跳过指标向量化")

        values = await self.meta_repo.list_all_values()
        if values:
            await self.value_es_repo.ensure_index()
            saved = await self.value_es_repo.save_batch(values)
            logger.info("取值字典入库 ES: {} 条", saved)
        else:
            logger.warning("meta 库 value_info 为空，跳过取值索引")

    def _embedding_size(self) -> int:
        return getattr(self.embedding_client, "embedding_dimensions", 1024)

    async def _embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        """按每批 BATCH_SIZE 批量向量化，返回与 texts 等长的向量列表。"""
        embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            embeddings.extend(await self.embedding_client.aembed_documents(texts[i : i + BATCH_SIZE]))
        return embeddings

    async def _upsert_columns(self, columns: list[ColumnInfo]) -> None:
        entries: list[tuple[str, list[float], ColumnInfo]] = []
        for c in columns:
            for point_id, text in _semantic_entries(c.id, c.name, c.description or "", c.alias or []):
                entries.append((point_id, text, c))
        if not entries:
            return
        embeddings = await self._embed_in_batches([t for _, t, _ in entries])
        # Qdrant 仅接受整数/UUID point id，用确定性 UUID 便于重复构建幂等
        await self.column_qdrant_repo.upsert(
            [(str(uuid.uuid5(uuid.NAMESPACE_URL, pid)), emb, c)
             for (pid, _, c), emb in zip(entries, embeddings, strict=False)]
        )
        logger.info("字段元数据入库 Qdrant: {} 个语义入口 / {} 个字段", len(entries), len(columns))

    async def _upsert_metrics(self, metrics: list[MetricInfo]) -> None:
        entries: list[tuple[str, list[float], MetricInfo]] = []
        for m in metrics:
            for point_id, text in _semantic_entries(m.id, m.name, m.description or "", m.alias or []):
                entries.append((point_id, text, m))
        if not entries:
            return
        embeddings = await self._embed_in_batches([t for _, t, _ in entries])
        # 同上：确定性 UUID point id
        await self.metric_qdrant_repo.upsert(
            [(str(uuid.uuid5(uuid.NAMESPACE_URL, pid)), emb, m)
             for (pid, _, m), emb in zip(entries, embeddings, strict=False)]
        )
        logger.info("指标元数据入库 Qdrant: {} 个语义入口 / {} 个指标", len(entries), len(metrics))
