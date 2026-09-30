-- ============================================================
-- schedule_meta 知识库表 DDL（问数 Agent 元数据）
-- 库：schedule_meta
-- 表：table_info / column_info / metric_info / value_info
-- ============================================================

USE schedule_meta;

-- 表元数据：业务表名/角色/描述，供合并节点组装表结构上下文
CREATE TABLE IF NOT EXISTS table_info (
    id          VARCHAR(64)  NOT NULL COMMENT '主键（表名，与 column_info.table_id 一致）',
    name        VARCHAR(128) NOT NULL COMMENT '展示名',
    role        VARCHAR(32)  DEFAULT NULL COMMENT 'dim/fact',
    description TEXT         DEFAULT NULL COMMENT '表业务说明',
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '表元数据';

-- 字段元数据：描述业务表的一个字段，供 LLM 生成 SQL 时理解语义
CREATE TABLE IF NOT EXISTS column_info (
    id          VARCHAR(64)  NOT NULL COMMENT '主键',
    name        VARCHAR(128) NOT NULL COMMENT '字段名',
    type        VARCHAR(64)  DEFAULT NULL COMMENT '字段类型',
    role        VARCHAR(32)  DEFAULT NULL COMMENT 'dimension/measure/date/pk/fk',
    examples    JSON         DEFAULT NULL COMMENT '示例值',
    description TEXT         DEFAULT NULL COMMENT '字段描述',
    alias       JSON         DEFAULT NULL COMMENT '别名列表',
    table_id    VARCHAR(64)  NOT NULL COMMENT '所属表',
    PRIMARY KEY (id),
    KEY idx_column_table (table_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '字段元数据';

-- 指标元数据：可计算的指标定义（胜率、场均得分等）
CREATE TABLE IF NOT EXISTS metric_info (
    id          VARCHAR(64)  NOT NULL COMMENT '主键',
    name        VARCHAR(128) NOT NULL COMMENT '指标名',
    agg_type    VARCHAR(32)  DEFAULT NULL COMMENT 'count/sum/avg/max/min/custom',
    expression  TEXT         DEFAULT NULL COMMENT '可拼入 SQL 的表达式',
    description TEXT         DEFAULT NULL COMMENT '描述',
    alias       JSON         DEFAULT NULL COMMENT '别名列表',
    table_id    VARCHAR(64)  NOT NULL COMMENT '所属表',
    PRIMARY KEY (id),
    KEY idx_metric_table (table_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '指标元数据';

-- 取值字典：字段常见取值（供 ES 分词检索，把口语实体名解析为库内标准值）
CREATE TABLE IF NOT EXISTS value_info (
    id          VARCHAR(64)  NOT NULL COMMENT '主键',
    field_name  VARCHAR(128) NOT NULL COMMENT '所属字段',
    value       VARCHAR(255) NOT NULL COMMENT '标准取值',
    aliases     VARCHAR(1024) DEFAULT NULL COMMENT '别名（逗号分隔）',
    description TEXT         DEFAULT NULL COMMENT '描述',
    PRIMARY KEY (id),
    KEY idx_value_field (field_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '取值字典';
