"""
召回信息合并节点

负责把字段 字段取值和指标三路召回结果聚合成统一上下文
这一层会补齐指标依赖字段 字段真实取值 主外键字段和表信息
后续过滤节点不再关心信息来自哪个检索分支，只处理合并后的表上下文和指标上下文
"""

from langgraph.runtime import Runtime

from app.agent.context import TournamentAgentContext
from app.agent.state import (
    ColumnInfoState,
    MetricInfoState,
    TableInfoState,
    TournamentAgentState,
)
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo


async def merge_retrieved_info(
    state: TournamentAgentState, runtime: Runtime[TournamentAgentContext]
):
    """合并召回结果，并输出 SQL 生成前的候选表信息和指标信息"""

    writer = runtime.stream_writer
    step = "合并召回信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        retrieved_column_infos: list[ColumnInfo] = state["retrieved_column_infos"]
        retrieved_metric_infos: list[MetricInfo] = state["retrieved_metric_infos"]
        retrieved_value_infos: list[ValueInfo] = state["retrieved_value_infos"]

        meta_mysql_repository = runtime.context["meta_mysql_repository"]

        # 本节点的主线是：
        # 字段召回 + 指标依赖字段 + 字段真实取值 + 主外键补齐
        # -> table_infos / metric_infos，交给后续过滤和 SQL 生成节点继续使用。

        # 1. 以 column_id 为 key 合并字段信息
        # 三路召回可能命中同一个字段，用 dict 可以自然去重；
        # 后续指标依赖字段和字段取值也都通过 column_id 合并进来。
        retrieved_column_infos_map: dict[str, ColumnInfo] = {
            retrieved_column_info.id: retrieved_column_info
            for retrieved_column_info in retrieved_column_infos
        }

        # 2. 补齐指标依赖字段
        # 指标告诉模型“怎么算”，但生成 SQL 还需要知道指标计算涉及的字段。
        # 指标通过 table_id 关联所属表；如果该表的字段没有被字段召回命中，
        # 就从 Meta MySQL 里按表查出来补进上下文。
        for retrieved_metric_info in retrieved_metric_infos:
            table_id = retrieved_metric_info.table_id
            if not table_id:
                continue
            if any(
                column_info.table_id == table_id
                for column_info in retrieved_column_infos_map.values()
            ):
                continue
            for column_info in await meta_mysql_repository.list_columns_by_table(
                table_id
            ):
                if column_info.id not in retrieved_column_infos_map:
                    retrieved_column_infos_map[column_info.id] = column_info

        # 3. 把字段取值合并回字段 examples
        # 字段取值召回命中的是 field_name + value，例如 team.name.某战队。
        # 把真实 value 放进字段 examples，可以帮助模型写出更接近真实数据的 where 条件。
        for retrieved_value_info in retrieved_value_infos:
            value = retrieved_value_info.value
            column_id = retrieved_value_info.field_name
            if column_id not in retrieved_column_infos_map:
                column_info: ColumnInfo = (
                    await meta_mysql_repository.get_column_info_by_id(column_id)
                )
                retrieved_column_infos_map[column_id] = column_info
            if value not in retrieved_column_infos_map[column_id].examples:
                retrieved_column_infos_map[column_id].examples.append(value)

        # 3.4 权限防线①（docs/permission-design.md 第 5 节）：兜底补列同样按角色可见表裁剪
        # （指标依赖字段 / 取值兜底 get_column_info_by_id 可能引入不可见表，这里统一拦截，
        #  同时保证后续 DB 取值兜底只发生在可见字段上）
        deny: set[str] = runtime.context.get("deny_tables") or set()
        allowed: set[str] = runtime.context.get("allowed_tables") or set()
        if deny or allowed:
            retrieved_column_infos_map = {
                cid: col
                for cid, col in retrieved_column_infos_map.items()
                if col.table_id not in deny and (not allowed or col.table_id in allowed)
            }

        # 3.5 DB 兜底：离线索引（ES/Qdrant）未收录的新值直接查 DW。
        # 新增赛事/队伍/选手后无需重跑 seed/build，这里用问题关键词对
        # 维度文本字段做 LIKE 检索，把真实值补进 examples。
        dw_mysql_repository = runtime.context["dw_mysql_repository"]
        value_keywords = [k for k in state["keywords"] if k] or [state["query"]]
        for column_info in retrieved_column_infos_map.values():
            if column_info.role != "dimension":
                continue
            col_type = (column_info.type or "").lower()
            if "char" not in col_type and "text" not in col_type:
                continue
            for keyword in value_keywords:
                if not keyword or len(keyword) < 2:
                    continue
                try:
                    db_values = await dw_mysql_repository.search_column_values(
                        column_info.table_id, column_info.name, keyword, limit=3
                    )
                except Exception as exc:  # 兜底失败不影响主流程
                    logger.warning(f"DB 兜底查询失败 {column_info.table_id}.{column_info.name}: {exc}")
                    continue
                for value in db_values:
                    if value not in column_info.examples:
                        column_info.examples.append(value)
                    if len(column_info.examples) >= 20:  # 防止上下文膨胀
                        break
                if len(column_info.examples) >= 20:
                    break

        # 4. 按表组织字段上下文
        # SQL 生成提示词通常按“表 -> 字段列表”的方式描述结构，
        # 所以这里先把分散的字段按 table_id 归到各自所属表下面。
        table_to_columns_map: dict[str, list[ColumnInfo]] = {}
        for column_info in retrieved_column_infos_map.values():
            table_id = column_info.table_id
            if table_id not in table_to_columns_map:
                table_to_columns_map[table_id] = []
            table_to_columns_map[table_id].append(column_info)

        # 5. 补齐主外键字段
        # 主外键通常不会出现在用户问题里，单靠向量召回容易漏掉；
        # 但多表查询的 Join 路径必须依赖它们，所以每张候选表都要兜底补齐。
        for table_id in table_to_columns_map.keys():
            key_columns: list[
                ColumnInfo
            ] = await meta_mysql_repository.get_key_columns_by_table_id(table_id)
            column_ids = [
                column_info.id for column_info in table_to_columns_map[table_id]
            ]
            for key_column in key_columns:
                if key_column.id not in column_ids:
                    table_to_columns_map[table_id].append(key_column)

        # 6. 生成表结构上下文
        # 数据库实体里可能包含入库和索引用字段，传给模型前只保留必要信息，
        # 让后续过滤和 SQL 生成节点面对的是更稳定的 TableInfoState 结构。
        table_infos: list[TableInfoState] = []
        for table_id, column_infos in table_to_columns_map.items():
            table_info: TableInfo = await meta_mysql_repository.get_table_info_by_id(
                table_id
            )
            columns = [
                ColumnInfoState(
                    name=column_info.name,
                    type=column_info.type,
                    role=column_info.role,
                    examples=column_info.examples,
                    description=column_info.description,
                    alias=column_info.alias,
                )
                for column_info in column_infos
            ]
            table_info_state = TableInfoState(
                name=table_info.name,
                role=table_info.role,
                description=table_info.description,
                columns=columns,
            )
            table_infos.append(table_info_state)

        # 7. 生成指标上下文
        # 指标上下文保留名称 聚合方式 表达式 别名和所属表，足够让模型理解业务口径。
        metric_infos: list[MetricInfoState] = [
            MetricInfoState(
                name=retrieved_metric_info.name,
                agg_type=retrieved_metric_info.agg_type,
                expression=retrieved_metric_info.expression,
                description=retrieved_metric_info.description,
                alias=retrieved_metric_info.alias,
                table_id=retrieved_metric_info.table_id,
            )
            for retrieved_metric_info in retrieved_metric_infos
        ]

        logger.info(
            f"合并后的表信息：{[table_info['name'] for table_info in table_infos]}"
        )
        logger.info(
            f"合并后的指标信息：{[metric_info['name'] for metric_info in metric_infos]}"
        )

        writer({"type": "progress", "step": step, "status": "success"})
        return {
            "table_infos": table_infos,
            "metric_infos": metric_infos,
        }
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
