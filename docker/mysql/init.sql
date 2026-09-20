-- 赛事管理 Agent 数据库初始化
-- schedule_meta：知识库元数据（column_info/metric_info/value_info，问数 Agent 用）
-- schedule_dw ：赛事业务数据（app_user/tournament/team/player/schedule 等 8 张业务表）

CREATE DATABASE IF NOT EXISTS schedule_meta DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS schedule_dw   DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON schedule_meta.* TO 'buyige'@'%';
GRANT ALL PRIVILEGES ON schedule_dw.*   TO 'buyige'@'%';
FLUSH PRIVILEGES;
