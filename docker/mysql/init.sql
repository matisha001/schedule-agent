-- 赛事管理 Agent 数据库初始化
-- meta：元数据库（表结构元数据、赛事/球队字典等知识库）
-- dw  ：赛事事实数据仓库（比赛、赛程、比分、排名等）

CREATE DATABASE IF NOT EXISTS meta DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS dw   DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON meta.* TO 'your_user'@'%';
GRANT ALL PRIVILEGES ON dw.*   TO 'your_user'@'%';
FLUSH PRIVILEGES;
