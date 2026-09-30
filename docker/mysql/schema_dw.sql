-- ============================================================
-- schedule_dw 业务表 DDL（赛事管理最小流程可流转）
-- 库：schedule_dw
-- 表：app_user / tournament / tournament_phase
--      team / player / schedule
-- 主键：全部自增 INT（不再落库外部系统 ID）
-- ============================================================

USE schedule_dw;

-- 1. 用户（id=1 为系统虚拟用户，TEMP 选手占位）
CREATE TABLE IF NOT EXISTS app_user (
    id         INT          NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    guid       BIGINT       DEFAULT NULL COMMENT '平台 GUID',
    nickname   VARCHAR(64)  NOT NULL COMMENT '昵称',
    phone      VARCHAR(32)  DEFAULT NULL COMMENT '手机号',
    password_hash VARCHAR(255) DEFAULT NULL COMMENT '密码哈希(PBKDF2)',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户基础信息';

-- 2. 赛事（列表 + 基础配置 + 报名规则）
CREATE TABLE IF NOT EXISTS tournament (
    id                INT          NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    name              VARCHAR(128) NOT NULL COMMENT '赛事名称',
    created_by        INT          NOT NULL COMMENT '主办方用户 ID',
    game              VARCHAR(64)  DEFAULT NULL COMMENT '游戏项目',
    game_maps         VARCHAR(2000) DEFAULT NULL COMMENT '可选地图(自由文本)',
    team_mode         TINYINT      NOT NULL DEFAULT 1 COMMENT '1团队赛 2个人赛',
    start_time        DATETIME     DEFAULT NULL COMMENT '赛事开始',
    end_time          DATETIME     DEFAULT NULL COMMENT '赛事结束',
    reg_start_time    DATETIME     DEFAULT NULL COMMENT '报名开始',
    reg_end_time      DATETIME     DEFAULT NULL COMMENT '报名结束',
    max_team_members  INT          NOT NULL DEFAULT 5 COMMENT '队伍最大成员数',
    max_teams         INT          NOT NULL DEFAULT 16 COMMENT '队伍数量上限',
    regist_method     TINYINT      NOT NULL DEFAULT 1 COMMENT '1办赛者代报名 2选手自主报名',
    contact_requirement VARCHAR(255) DEFAULT NULL COMMENT '联系方式要求(自由文本)',
    rule_info         VARCHAR(2000) DEFAULT NULL COMMENT '比赛规则(自由文本)',
    status            TINYINT      NOT NULL DEFAULT 0 COMMENT '0草稿 1已发布 2报名中 3比赛中 4已结束',
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_tournament_created_by (created_by),
    CONSTRAINT fk_tournament_user FOREIGN KEY (created_by) REFERENCES app_user (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '赛事';

-- 3. 赛事阶段（基础信息：名称/时间/状态）
CREATE TABLE IF NOT EXISTS tournament_phase (
    id            INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    tournament_id INT         NOT NULL COMMENT '所属赛事',
    name          VARCHAR(32) NOT NULL COMMENT '阶段名称(初赛/总决赛)',
    start_time    DATETIME    DEFAULT NULL COMMENT '阶段开始',
    end_time      DATETIME    DEFAULT NULL COMMENT '阶段结束',
    status        TINYINT     NOT NULL DEFAULT 0 COMMENT '阶段状态 0未开始 1进行中 2已结束',
    PRIMARY KEY (id),
    KEY idx_phase_tournament (tournament_id),
    CONSTRAINT fk_phase_tournament FOREIGN KEY (tournament_id) REFERENCES tournament (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '赛事阶段';

-- 4. 队伍（报名管理；个人赛按单人队伍复用）
CREATE TABLE IF NOT EXISTS team (
    id            INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    tournament_id INT         NOT NULL COMMENT '报名的赛事',
    name          VARCHAR(64) NOT NULL COMMENT '队伍名',
    status        TINYINT     NOT NULL DEFAULT 0 COMMENT '0待审核 1已确认 2已驳回 3已取消',
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报名时间',
    PRIMARY KEY (id),
    KEY idx_team_tournament (tournament_id),
    CONSTRAINT fk_team_tournament FOREIGN KEY (tournament_id) REFERENCES tournament (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '报名队伍';

-- 5. 选手
CREATE TABLE IF NOT EXISTS player (
    id          INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    team_id     INT         NOT NULL COMMENT '所属队伍',
    user_id     INT         DEFAULT NULL COMMENT '平台用户(可空;TEMP 可指虚拟 user id=1)',
    nickname    VARCHAR(64) NOT NULL COMMENT '昵称',
    is_captain  TINYINT     NOT NULL DEFAULT 0 COMMENT '是否队长',
    status      VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'AGREED/PENDING/REJECTED',
    player_type VARCHAR(16) NOT NULL DEFAULT 'TEMP' COMMENT 'TEMP临时 REAL正式',
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    PRIMARY KEY (id),
    KEY idx_player_team (team_id),
    KEY idx_player_user (user_id),
    CONSTRAINT fk_player_team FOREIGN KEY (team_id) REFERENCES team (id),
    CONSTRAINT fk_player_user FOREIGN KEY (user_id) REFERENCES app_user (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '选手';

-- 6. 赛程/对局（比赛管理 + 对局管理）
CREATE TABLE IF NOT EXISTS schedule (
    id             INT         NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    tournament_id  INT         NOT NULL COMMENT '所属赛事',
    phase_id       INT         NOT NULL COMMENT '所属阶段',
    round          INT         NOT NULL DEFAULT 1 COMMENT '轮次序号',
    round_name     VARCHAR(32) DEFAULT NULL COMMENT '轮次名(总决赛)',
    bo             INT         NOT NULL DEFAULT 1 COMMENT 'BO局数(1/3/5)',
    is_final       TINYINT     NOT NULL DEFAULT 0 COMMENT '是否决赛',
    home_team_id   INT         DEFAULT NULL COMMENT '主队',
    away_team_id   INT         DEFAULT NULL COMMENT '客队',
    home_score     INT         DEFAULT NULL COMMENT '主队比分',
    away_score     INT         DEFAULT NULL COMMENT '客队比分',
    status         TINYINT     NOT NULL DEFAULT 0 COMMENT '0未开赛 1进行中 2已结束 3已取消',
    start_time     DATETIME    DEFAULT NULL COMMENT '开赛时间',
    created_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_schedule_tournament (tournament_id),
    KEY idx_schedule_phase (phase_id),
    KEY idx_schedule_home (home_team_id),
    KEY idx_schedule_away (away_team_id),
    CONSTRAINT fk_schedule_tournament FOREIGN KEY (tournament_id) REFERENCES tournament (id),
    CONSTRAINT fk_schedule_phase FOREIGN KEY (phase_id) REFERENCES tournament_phase (id),
    CONSTRAINT fk_schedule_home FOREIGN KEY (home_team_id) REFERENCES team (id),
    CONSTRAINT fk_schedule_away FOREIGN KEY (away_team_id) REFERENCES team (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '赛程/对局';
