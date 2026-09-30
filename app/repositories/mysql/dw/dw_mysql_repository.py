"""DWMySQLRepository：赛事业务数据访问。

- run_select：执行校验后的只读 SQL（问数 Agent 用）
- 其余方法：基于 ORM + Mapper 的常用业务查询（赛事/阶段/队伍/选手/赛程）
依赖连接池初始化由 lifespan 完成。
"""

from sqlalchemy import delete, func, select, text

from app.clients.mysql_client_manager import dw_mysql_client_manager
from app.entities.app_user_info import AppUserInfo
from app.entities.organizer_application_info import OrganizerApplicationInfo
from app.entities.player_info import PlayerInfo
from app.entities.schedule_info import ScheduleInfo
from app.entities.team_info import TeamInfo
from app.entities.tournament_info import TournamentInfo
from app.entities.tournament_phase_info import TournamentPhaseInfo
from app.models.app_user_info import AppUserInfoMySQL
from app.models.organizer_application_info import OrganizerApplicationMySQL
from app.models.player_info import PlayerInfoMySQL
from app.models.schedule_info import ScheduleInfoMySQL
from app.models.team_info import TeamInfoMySQL
from app.models.tournament_info import TournamentInfoMySQL
from app.models.tournament_phase_info import TournamentPhaseInfoMySQL
from app.repositories.mysql.dw.mappers.app_user_mapper import AppUserMapper
from app.repositories.mysql.dw.mappers.organizer_application_mapper import (
    OrganizerApplicationMapper,
)
from app.repositories.mysql.dw.mappers.player_mapper import PlayerMapper
from app.repositories.mysql.dw.mappers.schedule_mapper import ScheduleMapper
from app.repositories.mysql.dw.mappers.team_mapper import TeamMapper
from app.repositories.mysql.dw.mappers.tournament_mapper import TournamentMapper
from app.repositories.mysql.dw.mappers.tournament_phase_mapper import (
    TournamentPhaseMapper,
)


class DWMySQLRepository:
    async def run_select(self, sql: str) -> tuple[list[str], list[dict]]:
        """执行只读 SQL，返回 (列名, 行列表)。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(text(sql))
            rows = result.fetchall()
            columns = list(result.keys())
            return columns, [dict(zip(columns, row)) for row in rows]

    async def get_db_info(self) -> dict:
        """读取当前数仓的方言和版本，供 SQL 生成提示词使用（docs/ag.md 节点 8）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            dialect = session.bind.dialect.name
            return {"dialect": dialect, "version": version}

    async def validate(self, sql: str) -> None:
        """用 EXPLAIN 让数据库提前解析 SQL，发现语法/表名/字段名错误（docs/ag.md 节点 10）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(text(f"EXPLAIN {sql}"))

    # ---------- 离线构建辅助：元数据库建库/取值采样（docs/ag.md 8.2） ----------

    async def get_table_schema(self, tables: list[str]) -> list[dict]:
        """读取指定表的字段结构（类型/注释/主外键），供离线构建推导字段元数据。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name, "
                    "COLUMN_TYPE AS column_type, DATA_TYPE AS data_type, COLUMN_COMMENT AS comment "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN :tables "
                    "ORDER BY TABLE_NAME, ORDINAL_POSITION"
                ),
                {"tables": tuple(tables)},
            )
            rows = result.mappings().fetchall()

            pk_rows = await session.execute(
                text(
                    "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_NAME = 'PRIMARY'"
                )
            )
            pk_set = {(r["TABLE_NAME"], r["COLUMN_NAME"]) for r in pk_rows.mappings().fetchall()}

            fk_rows = await session.execute(
                text(
                    "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL"
                )
            )
            fk_set = {(r["TABLE_NAME"], r["COLUMN_NAME"]) for r in fk_rows.mappings().fetchall()}

        return [
            {
                "table": r["table_name"], "column": r["column_name"],
                "type": r["column_type"], "data_type": r["data_type"],
                "comment": r["comment"] or "",
                "is_pk": (r["table_name"], r["column_name"]) in pk_set,
                "is_fk": (r["table_name"], r["column_name"]) in fk_set,
            }
            for r in rows
        ]

    async def search_column_values(self, table: str, column: str, keyword: str, limit: int = 5) -> list[str]:
        """按关键词 LIKE 搜索字段真实取值（离线索引未收录新值时的 DB 兜底）。

        keyword 来自用户问题/LLM 扩展，做参数化 + LIKE 通配符转义防注入；
        表名/列名来自 meta 配置（受控输入），仍以反引号包裹。
        """
        escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        # 表名/列名来自 meta 配置（受控），LIKE 值用参数化防注入，LIMIT 用 int 强转
        sql = (
            f"SELECT DISTINCT `{column}` FROM `{table}` "
            f"WHERE `{column}` LIKE :kw AND `{column}` IS NOT NULL LIMIT {int(limit)}"
        )
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(text(sql), {"kw": f"%{escaped}%"})
            return [str(r[0]) for r in result.fetchall()]

    async def get_column_values(self, table: str, column: str, limit: int = 8) -> list[str]:
        """抽样取字段真实取值（去重，最多 limit 个），供元数据入库和检索链路复用。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                text(
                    f"SELECT DISTINCT `{column}` FROM `{table}` "
                    f"WHERE `{column}` IS NOT NULL LIMIT {int(limit)}"
                )
            )
            return [str(r[0]) for r in result.fetchall()]

    # ---------- 赛事 ----------
    async def list_tournaments(self) -> list[TournamentInfo]:
        """赛事列表。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TournamentInfoMySQL).order_by(TournamentInfoMySQL.id.desc())
            )
            return [TournamentMapper.to_entity(row) for row in result.scalars().all()]

    async def get_tournament(self, tournament_id: int) -> TournamentInfo | None:
        """按 ID 查赛事。"""
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TournamentInfoMySQL, tournament_id)
            return TournamentMapper.to_entity(row) if row else None

    # ---------- 阶段 ----------
    async def list_phases(self, tournament_id: int) -> list[TournamentPhaseInfo]:
        """按赛事查阶段（按 ID 排序）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TournamentPhaseInfoMySQL)
                .where(TournamentPhaseInfoMySQL.tournament_id == tournament_id)
                .order_by(TournamentPhaseInfoMySQL.id)
            )
            return [TournamentPhaseMapper.to_entity(row) for row in result.scalars().all()]

    # ---------- 队伍 ----------
    async def list_teams(self, tournament_id: int) -> list[TeamInfo]:
        """按赛事查报名队伍。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TeamInfoMySQL)
                .where(TeamInfoMySQL.tournament_id == tournament_id)
                .order_by(TeamInfoMySQL.id)
            )
            return [TeamMapper.to_entity(row) for row in result.scalars().all()]

    # ---------- 选手 ----------
    async def list_players(self, team_id: int) -> list[PlayerInfo]:
        """按队伍查选手。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(PlayerInfoMySQL)
                .where(PlayerInfoMySQL.team_id == team_id)
                .order_by(PlayerInfoMySQL.id)
            )
            return [PlayerMapper.to_entity(row) for row in result.scalars().all()]

    # ---------- 赛程/对局 ----------
    async def list_schedules(self, tournament_id: int) -> list[ScheduleInfo]:
        """按赛事查全部对局。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(ScheduleInfoMySQL)
                .where(ScheduleInfoMySQL.tournament_id == tournament_id)
                .order_by(ScheduleInfoMySQL.phase_id, ScheduleInfoMySQL.round)
            )
            return [ScheduleMapper.to_entity(row) for row in result.scalars().all()]

    async def get_schedule(self, schedule_id: int) -> ScheduleInfo | None:
        """按 ID 查对局。"""
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(ScheduleInfoMySQL, schedule_id)
            return ScheduleMapper.to_entity(row) if row else None

    # ================= 用户 =================
    async def find_user_by_phone(self, phone: str) -> AppUserInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(AppUserInfoMySQL).where(AppUserInfoMySQL.phone == phone)
            )
            row = result.scalars().first()
            return AppUserMapper.to_entity(row) if row else None

    async def get_user(self, user_id: int) -> AppUserInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(AppUserInfoMySQL, user_id)
            return AppUserMapper.to_entity(row) if row else None

    async def create_user(self, nickname: str, phone: str, password_hash: str | None = None) -> AppUserInfo:
        async with dw_mysql_client_manager.session_factory() as session:
            model = AppUserInfoMySQL(nickname=nickname, phone=phone, password_hash=password_hash)  # id 由数据库自增
            session.add(model)
            await session.commit()
            await session.refresh(model)  # 回读自增 id 与 server_default 字段
            return AppUserMapper.to_entity(model)

    async def update_user_password(self, user_id: int, password_hash: str) -> None:
        """更新用户密码哈希（首次设置 / 修改密码）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            model = await session.get(AppUserInfoMySQL, user_id)
            if model is None:
                raise ValueError(f"用户不存在: {user_id}")
            model.password_hash = password_hash
            await session.commit()

    # ---------- 用户管理（角色体系） ----------
    async def list_users(self, limit: int, offset: int) -> list[AppUserInfo]:
        """分页用户列表（按 id 倒序）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(AppUserInfoMySQL)
                .order_by(AppUserInfoMySQL.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return [AppUserMapper.to_entity(row) for row in result.scalars().all()]

    async def count_users(self) -> int:
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(AppUserInfoMySQL)
            )
            return int(result.scalar_one())

    async def count_users_by_role(self, role: str) -> int:
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(AppUserInfoMySQL)
                .where(AppUserInfoMySQL.role == role)
            )
            return int(result.scalar_one())

    async def update_user_role(self, user_id: int, role: str) -> AppUserInfo | None:
        """更新用户角色，返回更新后的用户（不存在返回 None）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            model = await session.get(AppUserInfoMySQL, user_id)
            if model is None:
                return None
            model.role = role
            await session.commit()
            return AppUserMapper.to_entity(model)

    # ---------- 账号资料与软注销 ----------
    async def update_user_nickname(self, user_id: int, nickname: str) -> AppUserInfo | None:
        """更新昵称，返回更新后的用户（不存在返回 None）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            model = await session.get(AppUserInfoMySQL, user_id)
            if model is None:
                return None
            model.nickname = nickname
            await session.commit()
            return AppUserMapper.to_entity(model)

    async def soft_delete_user(self, user_id: int) -> AppUserInfo | None:
        """软注销：置 deleted_at 并匿名化昵称（历史赛事/报名数据保留）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            model = await session.get(AppUserInfoMySQL, user_id)
            if model is None:
                return None
            from sqlalchemy import func as _func

            model.deleted_at = _func.now()
            model.nickname = f"已注销用户{model.id}"
            await session.commit()
            return AppUserMapper.to_entity(model)

    # ---------- 办赛申请（玩家 → 办赛者） ----------
    async def create_organizer_application(
        self, user_id: int, reason: str | None = None
    ) -> OrganizerApplicationInfo:
        async with dw_mysql_client_manager.session_factory() as session:
            model = OrganizerApplicationMySQL(user_id=user_id, reason=reason)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return OrganizerApplicationMapper.to_entity(model)

    async def get_organizer_application(self, app_id: int) -> OrganizerApplicationInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(OrganizerApplicationMySQL, app_id)
            return OrganizerApplicationMapper.to_entity(row) if row else None

    async def find_latest_application_by_user(self, user_id: int) -> OrganizerApplicationInfo | None:
        """用户最新一条办赛申请（用于展示状态 / 防重复提交）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(OrganizerApplicationMySQL)
                .where(OrganizerApplicationMySQL.user_id == user_id)
                .order_by(OrganizerApplicationMySQL.id.desc())
                .limit(1)
            )
            row = result.scalars().first()
            return OrganizerApplicationMapper.to_entity(row) if row else None

    async def list_organizer_applications(
        self, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[OrganizerApplicationInfo]:
        """审批列表：按申请时间倒序，可按状态筛选。"""
        async with dw_mysql_client_manager.session_factory() as session:
            query = select(OrganizerApplicationMySQL).order_by(
                OrganizerApplicationMySQL.id.desc()
            )
            if status:
                query = query.where(OrganizerApplicationMySQL.status == status)
            result = await session.execute(query.limit(limit).offset(offset))
            return [
                OrganizerApplicationMapper.to_entity(row)
                for row in result.scalars().all()
            ]

    async def count_organizer_applications(self, status: str | None = None) -> int:
        async with dw_mysql_client_manager.session_factory() as session:
            query = select(func.count()).select_from(OrganizerApplicationMySQL)
            if status:
                query = query.where(OrganizerApplicationMySQL.status == status)
            result = await session.execute(query)
            return int(result.scalar_one())

    async def review_organizer_application(
        self, app_id: int, status: str, reviewer_id: int
    ) -> OrganizerApplicationInfo | None:
        """审批申请（APPROVED/REJECTED），记录审批人与时间。"""
        async with dw_mysql_client_manager.session_factory() as session:
            model = await session.get(OrganizerApplicationMySQL, app_id)
            if model is None:
                return None
            from sqlalchemy import func as _func

            model.status = status
            model.reviewed_by = reviewer_id
            model.reviewed_at = _func.now()
            await session.commit()
            return OrganizerApplicationMapper.to_entity(model)

    # ================= 赛事（写） =================
    async def create_tournament(self, entity: TournamentInfo) -> TournamentInfo:
        entity.id = None  # 数据库自增
        async with dw_mysql_client_manager.session_factory() as session:
            model = TournamentMapper.to_model(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)  # 回读自增 id 与 server_default 字段
            entity.id = model.id
            return entity

    async def update_tournament(self, entity: TournamentInfo) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TournamentInfoMySQL, entity.id)
            if row is None:
                return
            for field, value in TournamentMapper.to_model(entity).__dict__.items():
                if field.startswith("_"):
                    continue
                setattr(row, field, value)
            await session.commit()

    async def delete_tournament_cascade(self, tournament_id: int) -> None:
        """级联删除：schedules → players → teams → phases → tournament。"""
        async with dw_mysql_client_manager.session_factory() as session:
            team_ids = select(TeamInfoMySQL.id).where(
                TeamInfoMySQL.tournament_id == tournament_id
            )
            await session.execute(delete(PlayerInfoMySQL).where(PlayerInfoMySQL.team_id.in_(team_ids)))
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.tournament_id == tournament_id))
            await session.execute(delete(TeamInfoMySQL).where(TeamInfoMySQL.tournament_id == tournament_id))
            await session.execute(delete(TournamentPhaseInfoMySQL).where(TournamentPhaseInfoMySQL.tournament_id == tournament_id))
            await session.execute(delete(TournamentInfoMySQL).where(TournamentInfoMySQL.id == tournament_id))
            await session.commit()

    async def list_tournaments_by_creator(self, creator_id: int) -> list[TournamentInfo]:
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TournamentInfoMySQL)
                .where(TournamentInfoMySQL.created_by == creator_id)
                .order_by(TournamentInfoMySQL.id.desc())
            )
            return [TournamentMapper.to_entity(row) for row in result.scalars().all()]

    async def list_published_tournaments(self) -> list[TournamentInfo]:
        """官网可见：status >= 1（已发布及以上）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TournamentInfoMySQL)
                .where(TournamentInfoMySQL.status >= 1)
                .order_by(TournamentInfoMySQL.id.desc())
            )
            return [TournamentMapper.to_entity(row) for row in result.scalars().all()]

    async def list_tournaments_by_user(self, user_id: int) -> list[TournamentInfo]:
        """玩家报名参加过的赛事（通过 player.user_id 关联）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TournamentInfoMySQL)
                .join(TeamInfoMySQL, TeamInfoMySQL.tournament_id == TournamentInfoMySQL.id)
                .join(PlayerInfoMySQL, PlayerInfoMySQL.team_id == TeamInfoMySQL.id)
                .where(PlayerInfoMySQL.user_id == user_id)
                .distinct()
                .order_by(TournamentInfoMySQL.id.desc())
            )
            return [TournamentMapper.to_entity(row) for row in result.scalars().all()]

    async def count_teams(self, tournament_id: int, status: int | None = None) -> int:
        async with dw_mysql_client_manager.session_factory() as session:
            query = select(func.count()).select_from(TeamInfoMySQL).where(
                TeamInfoMySQL.tournament_id == tournament_id
            )
            if status is not None:
                query = query.where(TeamInfoMySQL.status == status)
            result = await session.execute(query)
            return int(result.scalar_one())

    async def count_players(self, tournament_id: int) -> int:
        async with dw_mysql_client_manager.session_factory() as session:
            team_ids = select(TeamInfoMySQL.id).where(
                TeamInfoMySQL.tournament_id == tournament_id
            )
            result = await session.execute(
                select(func.count())
                .select_from(PlayerInfoMySQL)
                .where(PlayerInfoMySQL.team_id.in_(team_ids))
            )
            return int(result.scalar_one())

    # ================= 阶段（写） =================
    async def get_phase(self, phase_id: int) -> TournamentPhaseInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TournamentPhaseInfoMySQL, phase_id)
            return TournamentPhaseMapper.to_entity(row) if row else None

    async def create_phase(self, entity: TournamentPhaseInfo) -> TournamentPhaseInfo:
        entity.id = None  # 数据库自增
        async with dw_mysql_client_manager.session_factory() as session:
            model = TournamentPhaseMapper.to_model(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            entity.id = model.id
            return entity

    async def update_phase(self, entity: TournamentPhaseInfo) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TournamentPhaseInfoMySQL, entity.id)
            if row is None:
                return
            for field, value in TournamentPhaseMapper.to_model(entity).__dict__.items():
                if field.startswith("_"):
                    continue
                setattr(row, field, value)
            await session.commit()

    async def delete_phase(self, phase_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.phase_id == phase_id))
            await session.execute(delete(TournamentPhaseInfoMySQL).where(TournamentPhaseInfoMySQL.id == phase_id))
            await session.commit()

    async def delete_phases_by_tournament(self, tournament_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(
                delete(TournamentPhaseInfoMySQL).where(
                    TournamentPhaseInfoMySQL.tournament_id == tournament_id
                )
            )
            await session.commit()

    # ================= 队伍（写） =================
    async def get_team(self, team_id: int) -> TeamInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TeamInfoMySQL, team_id)
            return TeamMapper.to_entity(row) if row else None

    async def find_team_by_user(self, tournament_id: int, user_id: int) -> TeamInfo | None:
        """用户在指定赛事中的队伍（通过 player.user_id 关联）。"""
        async with dw_mysql_client_manager.session_factory() as session:
            result = await session.execute(
                select(TeamInfoMySQL)
                .join(PlayerInfoMySQL, PlayerInfoMySQL.team_id == TeamInfoMySQL.id)
                .where(
                    TeamInfoMySQL.tournament_id == tournament_id,
                    PlayerInfoMySQL.user_id == user_id,
                )
                .limit(1)
            )
            row = result.scalars().first()
            return TeamMapper.to_entity(row) if row else None

    async def create_team(self, entity: TeamInfo) -> TeamInfo:
        entity.id = None  # 数据库自增
        async with dw_mysql_client_manager.session_factory() as session:
            model = TeamMapper.to_model(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            entity.id = model.id
            return entity

    async def update_team(self, entity: TeamInfo) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(TeamInfoMySQL, entity.id)
            if row is None:
                return
            for field, value in TeamMapper.to_model(entity).__dict__.items():
                if field.startswith("_"):
                    continue
                setattr(row, field, value)
            await session.commit()

    async def delete_team(self, team_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(PlayerInfoMySQL).where(PlayerInfoMySQL.team_id == team_id))
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.home_team_id == team_id))
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.away_team_id == team_id))
            await session.execute(delete(TeamInfoMySQL).where(TeamInfoMySQL.id == team_id))
            await session.commit()

    async def delete_teams_by_tournament(self, tournament_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(TeamInfoMySQL).where(TeamInfoMySQL.tournament_id == tournament_id))
            await session.commit()

    # ================= 选手（写） =================
    async def get_player(self, player_id: int) -> PlayerInfo | None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(PlayerInfoMySQL, player_id)
            return PlayerMapper.to_entity(row) if row else None

    async def create_player(self, entity: PlayerInfo) -> PlayerInfo:
        entity.id = None  # 数据库自增
        async with dw_mysql_client_manager.session_factory() as session:
            model = PlayerMapper.to_model(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            entity.id = model.id
            return entity

    async def update_player(self, entity: PlayerInfo) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(PlayerInfoMySQL, entity.id)
            if row is None:
                return
            for field, value in PlayerMapper.to_model(entity).__dict__.items():
                if field.startswith("_"):
                    continue
                setattr(row, field, value)
            await session.commit()

    async def delete_player(self, player_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(PlayerInfoMySQL).where(PlayerInfoMySQL.id == player_id))
            await session.commit()

    async def delete_players_by_team(self, team_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(PlayerInfoMySQL).where(PlayerInfoMySQL.team_id == team_id))
            await session.commit()

    async def delete_players_by_tournament(self, tournament_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            team_ids = select(TeamInfoMySQL.id).where(
                TeamInfoMySQL.tournament_id == tournament_id
            )
            await session.execute(delete(PlayerInfoMySQL).where(PlayerInfoMySQL.team_id.in_(team_ids)))
            await session.commit()

    async def list_players_by_tournament(self, tournament_id: int) -> list[PlayerInfo]:
        async with dw_mysql_client_manager.session_factory() as session:
            team_ids = select(TeamInfoMySQL.id).where(
                TeamInfoMySQL.tournament_id == tournament_id
            )
            result = await session.execute(
                select(PlayerInfoMySQL)
                .where(PlayerInfoMySQL.team_id.in_(team_ids))
                .order_by(PlayerInfoMySQL.id)
            )
            return [PlayerMapper.to_entity(row) for row in result.scalars().all()]

    # ================= 赛程/对局（写） =================
    async def create_schedule(self, entity: ScheduleInfo) -> ScheduleInfo:
        entity.id = None  # 数据库自增
        async with dw_mysql_client_manager.session_factory() as session:
            model = ScheduleMapper.to_model(entity)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            entity.id = model.id
            return entity

    async def update_schedule(self, entity: ScheduleInfo) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            row = await session.get(ScheduleInfoMySQL, entity.id)
            if row is None:
                return
            for field, value in ScheduleMapper.to_model(entity).__dict__.items():
                if field.startswith("_"):
                    continue
                setattr(row, field, value)
            await session.commit()

    async def delete_schedule(self, schedule_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.id == schedule_id))
            await session.commit()

    async def delete_schedules_by_tournament(self, tournament_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(
                delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.tournament_id == tournament_id)
            )
            await session.commit()

    async def delete_schedules_by_phase(self, phase_id: int) -> None:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(delete(ScheduleInfoMySQL).where(ScheduleInfoMySQL.phase_id == phase_id))
            await session.commit()


dw_mysql_repository = DWMySQLRepository()
