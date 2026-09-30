"""入口脚本：生成/读取 conf/meta_config.yaml，并按其灌入 meta 元数据。

用法（脚本层只做参数解析、初始化、调度，业务编排在 MetaKnowledgeService）：
  uv run python -m app.scripts.seed_meta_knowledge   # 配置缺失时自动生成 conf/meta_config.yaml，再按配置灌入 meta

灌库为整表替换（幂等），重复执行安全。
"""

import argparse
import asyncio
from pathlib import Path

from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.conf.meta_config import load_meta_config
from app.core.log import logger
from app.repositories.es.value_es_repository import value_es_repository
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository
from app.repositories.mysql.meta.meta_mysql_repository import meta_mysql_repository
from app.repositories.qdrant.column_qdrant_repository import column_qdrant_repository
from app.repositories.qdrant.metric_qdrant_repository import metric_qdrant_repository
from app.services.meta_knowledge_service import MetaKnowledgeService

DEFAULT_CONF = Path(__file__).resolve().parents[2] / "conf" / "meta_config.yaml"


def _create_service() -> MetaKnowledgeService:
    # 灌入种子只访问 Meta MySQL 和 DW MySQL，索引类仓储随服务构造但不初始化连接
    return MetaKnowledgeService(
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
        embedding_client=None,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="生成/读取 meta_config.yaml 并灌入 meta 元数据")
    parser.add_argument("-c", "--conf", default=str(DEFAULT_CONF), help="meta_config.yaml 路径")
    args = parser.parse_args()

    # seed 只需要 Meta MySQL（写元数据）和 DW MySQL（读真实表结构/取值）
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    service = _create_service()
    conf_path = Path(args.conf)

    if not conf_path.exists():
        # 配置缺失：先基于 DW 表结构生成默认配置，再按配置灌库
        logger.info("conf/meta_config.yaml 不存在，先基于 DW 表结构生成默认配置")
        await service.generate_config(str(conf_path))
    await service.seed_meta(load_meta_config(str(conf_path)))

    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
