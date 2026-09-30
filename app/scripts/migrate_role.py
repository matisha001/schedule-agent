"""幂等迁移脚本：权限体系与账号能力所需表结构变更。

- app_user 补 role 列（旧库）
- app_user 补 deleted_at 列（软注销标记）
- 新建 organizer_application 表（玩家 → 办赛者申请）

新部署由 docker/mysql/schema_dw.sql 直接建表（已含全部变更）；
本脚本仅用于已有数据库补列/建表，重复执行安全。

用法：
  uv run python -m app.scripts.migrate_role
"""

import asyncio

from sqlalchemy import text

from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.core.log import logger


async def _column_exists(session, table: str, column: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = :table AND COLUMN_NAME = :col"
        ),
        {"table": table, "col": column},
    )
    return int(result.scalar()) > 0


async def _table_exists(session, table: str) -> bool:
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ),
        {"table": table},
    )
    return int(result.scalar()) > 0


async def main() -> None:
    dw_mysql_client_manager.init()
    try:
        async with dw_mysql_client_manager.session_factory() as session:
            # 1. app_user.role（旧库补列）
            if await _column_exists(session, "app_user", "role"):
                logger.info("app_user.role 列已存在，无需迁移")
            else:
                await session.execute(
                    text(
                        "ALTER TABLE app_user "
                        "ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'player' "
                        "COMMENT '角色: player/organizer/operator/super_admin'"
                    )
                )
                logger.info("已为 app_user 添加 role 列（默认 player）")

            # 2. app_user.deleted_at（软注销标记）
            if await _column_exists(session, "app_user", "deleted_at"):
                logger.info("app_user.deleted_at 列已存在，无需迁移")
            else:
                await session.execute(
                    text(
                        "ALTER TABLE app_user "
                        "ADD COLUMN deleted_at DATETIME DEFAULT NULL "
                        "COMMENT '注销时间(非空=已注销)'"
                    )
                )
                logger.info("已为 app_user 添加 deleted_at 列")

            # 3. organizer_application 表（办赛申请）
            if await _table_exists(session, "organizer_application"):
                logger.info("organizer_application 表已存在，无需创建")
            else:
                await session.execute(
                    text(
                        """
                        CREATE TABLE organizer_application (
                            id          INT          NOT NULL AUTO_INCREMENT,
                            user_id     INT          NOT NULL,
                            status      VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
                            reason      VARCHAR(255) DEFAULT NULL,
                            reviewed_by INT          DEFAULT NULL,
                            reviewed_at DATETIME     DEFAULT NULL,
                            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (id),
                            KEY idx_appl_user (user_id),
                            KEY idx_appl_status (status),
                            CONSTRAINT fk_appl_user FOREIGN KEY (user_id) REFERENCES app_user (id),
                            CONSTRAINT fk_appl_reviewer FOREIGN KEY (reviewed_by) REFERENCES app_user (id)
                        ) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '办赛申请'
                        """
                    )
                )
                logger.info("已创建 organizer_application 表")

            await session.commit()
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
