"""赛事业务服务：登录 / 赛事 CRUD 与状态流转 / 阶段 / 报名（队伍、选手）/ 对局管理。

职责：参数与权限校验（创建者、报名资格）、业务编排、返回可直接序列化的 dict。
数据访问统一走 dw_mysql_repository（读）+ 写方法（见 DWMySQLRepository）。
"""

import re
from typing import Any

from fastapi import HTTPException

from app.core.idgen import id_generator
from app.core.security import create_token
from app.entities.player_info import PlayerInfo
from app.entities.schedule_info import ScheduleInfo
from app.entities.team_info import TeamInfo
from app.entities.tournament_info import TournamentInfo
from app.entities.tournament_phase_info import TournamentPhaseInfo
from app.repositories.mysql.dw.dw_mysql_repository import dw_mysql_repository as repo
from app.services.security import hash_password, verify_password

# 状态常量
TOURNAMENT_STATUS: dict[int, str] = {0: "草稿", 1: "已发布", 2: "报名中", 3: "比赛中", 4: "已结束"}
TEAM_STATUS: dict[int, str] = {0: "待审核", 1: "已确认", 2: "已驳回", 3: "已取消"}
SCHEDULE_STATUS: dict[int, str] = {0: "未开赛", 1: "进行中", 2: "已结束", 3: "已取消"}
PHASE_STATUS: dict[int, str] = {0: "未开始", 1: "进行中", 2: "已结束"}

# 赛事状态流转：action -> (允许的当前状态集合, 目标状态)
TRANSITIONS: dict[str, tuple[set[int], int]] = {
    "publish": ({0}, 1),          # 发布
    "open": ({1}, 2),             # 开始报名
    "close": ({2}, 1),            # 结束报名
    "start": ({1, 2}, 3),         # 开始比赛
    "finish": ({3}, 4),           # 结束比赛
}

_PHONE_RE = re.compile(r"^1\d{10}$")


def _tournament_out(t: TournamentInfo, extra: dict | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": t.id,
        "name": t.name,
        "created_by": t.created_by,
        "game": t.game,
        "game_maps": t.game_maps,
        "team_mode": t.team_mode,
        "start_time": t.start_time,
        "end_time": t.end_time,
        "reg_start_time": t.reg_start_time,
        "reg_end_time": t.reg_end_time,
        "max_team_members": t.max_team_members,
        "max_teams": t.max_teams,
        "regist_method": t.regist_method,
        "contact_requirement": t.contact_requirement,
        "rule_info": t.rule_info,
        "status": t.status,
        "status_label": TOURNAMENT_STATUS.get(t.status, str(t.status)),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
    if extra:
        data.update(extra)
    return data


class TournamentService:
    # ---------- 登录 ----------
    async def login(self, phone: str, password: str) -> dict[str, Any]:
        """手机号 + 密码登录：新用户自动注册并设置密码；老用户校验密码。

        - 已设密码的用户：密码不匹配抛 401（统一报"手机号或密码错误"，不泄露账号存在性）
        - 历史无密码用户（password_hash 为空）：首次登录时设置密码，完成账号认领
        """
        phone = phone.strip()
        if not _PHONE_RE.match(phone):
            raise HTTPException(status_code=400, detail="请输入有效的 11 位手机号")
        if not 6 <= len(password) <= 64:
            raise HTTPException(status_code=400, detail="密码长度需为 6-64 位")

        user = await repo.find_user_by_phone(phone)
        if user is not None and user.deleted_at:
            raise HTTPException(status_code=401, detail="账号已注销，无法登录")
        if user is None:
            nickname = f"玩家{phone[-4:]}"
            user = await repo.create_user(nickname=nickname, phone=phone, password_hash=hash_password(password))
        elif user.password_hash is None:
            # 历史无密码用户：首次登录即设置密码（认领账号）
            await repo.update_user_password(user.id, hash_password(password))
            user.password_hash = None  # 实体不回传哈希
        elif not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="手机号或密码错误")

        token = create_token(user.id)
        return {
            "token": token,
            "user": {
                "id": user.id,
                "nickname": user.nickname,
                "phone": user.phone,
                "role": user.role,
                "created_at": user.created_at,
            },
        }

    # ---------- 赛事 ----------
    async def list_tournaments(self, scope: str, user_id: int | None = None) -> list[dict[str, Any]]:
        if scope == "mine":
            if user_id is None:
                raise HTTPException(status_code=401, detail="请先登录")
            tournaments = await repo.list_tournaments_by_creator(user_id)
        else:  # published
            tournaments = await repo.list_published_tournaments()
        result = []
        for t in tournaments:
            creator = await repo.get_user(t.created_by)
            result.append(
                _tournament_out(
                    t,
                    {
                        "created_by_nickname": creator.nickname if creator else "",
                        "team_count": await repo.count_teams(t.id),
                        "player_count": await repo.count_players(t.id),
                    },
                )
            )
        return result

    async def get_tournament_detail(self, tournament_id: int, user_id: int | None = None) -> dict[str, Any]:
        t = await self._get_tournament_or_404(tournament_id)
        if t.status == 0 and t.created_by != user_id:
            raise HTTPException(status_code=404, detail="赛事不存在或未发布")

        phases = await repo.list_phases(tournament_id)
        teams = await self._list_teams_with_players(tournament_id)
        my_team = None
        if user_id is not None:
            team = await repo.find_team_by_user(tournament_id, user_id)
            if team is not None:
                my_team = await self._team_out(team)

        confirmed_count = await repo.count_teams(tournament_id, status=1)
        pending_count = await repo.count_teams(tournament_id, status=0)
        can_register = bool(
            user_id is not None
            and t.created_by != user_id
            and t.status == 2
            and my_team is None
            and (confirmed_count + pending_count) < t.max_teams
        )

        return {
            **_tournament_out(t),
            "created_by_nickname": (await self._creator_nickname(t.created_by)),
            "phases": [self._phase_out(p) for p in phases],
            "teams": teams,
            "stats": {
                "team_count": len(teams),
                "confirmed_team_count": confirmed_count,
                "pending_team_count": pending_count,
                "player_count": sum(len(tm["players"]) for tm in teams),
            },
            "my_team": my_team,
            "can_register": can_register,
            "is_creator": user_id is not None and t.created_by == user_id,
        }

    async def create_tournament(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        t = TournamentInfo(id=0, name=payload["name"], created_by=user_id)
        self._apply_tournament_fields(t, payload)
        t.status = 0
        created = await repo.create_tournament(t)
        return _tournament_out(created)

    async def update_tournament(self, user_id: int, tournament_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        t = await self._require_creator(user_id, tournament_id)
        t.name = payload["name"]
        self._apply_tournament_fields(t, payload)
        await repo.update_tournament(t)
        return _tournament_out(t)

    async def delete_tournament(self, user_id: int, tournament_id: int) -> None:
        await self._require_creator(user_id, tournament_id)
        await repo.delete_tournament_cascade(tournament_id)

    async def transition(self, user_id: int, tournament_id: int, action: str) -> dict[str, Any]:
        t = await self._require_creator(user_id, tournament_id)
        rule = TRANSITIONS.get(action)
        if rule is None:
            raise HTTPException(status_code=400, detail="不支持的状态操作")
        allowed, target = rule
        if t.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"当前状态（{TOURNAMENT_STATUS.get(t.status)}）不能执行「{action}」",
            )
        t.status = target
        await repo.update_tournament(t)
        return _tournament_out(t)

    # ---------- 阶段 ----------
    async def list_phases(self, tournament_id: int) -> list[dict[str, Any]]:
        phases = await repo.list_phases(tournament_id)
        return [self._phase_out(p) for p in phases]

    async def create_phase(self, user_id: int, tournament_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        await self._require_creator(user_id, tournament_id)
        phase = TournamentPhaseInfo(
            id=id_generator.next_id(),
            tournament_id=tournament_id,
            name=payload["name"],
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time"),
            status=0,
        )
        created = await repo.create_phase(phase)
        return self._phase_out(created)

    async def update_phase(self, user_id: int, phase_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        phase = await repo.get_phase(phase_id)
        if phase is None:
            raise HTTPException(status_code=404, detail="阶段不存在")
        await self._require_creator(user_id, phase.tournament_id)
        phase.name = payload["name"]
        phase.start_time = payload.get("start_time")
        phase.end_time = payload.get("end_time")
        if payload.get("status") is not None:
            phase.status = payload["status"]
        await repo.update_phase(phase)
        return self._phase_out(phase)

    async def delete_phase(self, user_id: int, phase_id: int) -> None:
        phase = await repo.get_phase(phase_id)
        if phase is None:
            raise HTTPException(status_code=404, detail="阶段不存在")
        await self._require_creator(user_id, phase.tournament_id)
        await repo.delete_phase(phase_id)

    # ---------- 报名（队伍/选手） ----------
    async def list_teams(self, tournament_id: int) -> list[dict[str, Any]]:
        teams = await self._list_teams_with_players(tournament_id)
        return teams

    async def create_team(self, user_id: int, tournament_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        t = await self._get_tournament_or_404(tournament_id)
        if t.status != 2:
            raise HTTPException(status_code=400, detail="当前不在报名时间内")
        if t.created_by == user_id:
            raise HTTPException(status_code=400, detail="办赛者不能给自己创建的赛事报名")

        existing = await repo.find_team_by_user(tournament_id, user_id)
        if existing is not None:
            raise HTTPException(status_code=400, detail="你已报名过该赛事，请勿重复报名")

        pending = await repo.count_teams(tournament_id, status=0)
        confirmed = await repo.count_teams(tournament_id, status=1)
        if pending + confirmed >= t.max_teams:
            raise HTTPException(status_code=400, detail="队伍数量已达上限")

        players_payload = payload.get("players") or []
        if t.team_mode == 2:  # 个人赛：单人队伍
            # 优先使用提交的昵称（payload.name 为前端报名弹窗传参，也可从 players 取）
            solo_nickname = (payload.get("name") or "").strip() or (
                players_payload[0]["nickname"].strip() if players_payload else ""
            )
            team_name = solo_nickname or f"玩家{str(user_id)[-4:]}"
            members = [self._captain_player(user_id, team_name)]
        else:
            team_name = (payload.get("name") or "").strip()
            if not team_name:
                raise HTTPException(status_code=400, detail="请填写队伍名")
            if len(players_payload) + 1 > t.max_team_members:
                raise HTTPException(
                    status_code=400, detail=f"队伍最多 {t.max_team_members} 人（含队长）"
                )
            team = await repo.create_team(
                TeamInfo(id=0, tournament_id=tournament_id, name=team_name, status=0)
            )
            captain = self._captain_player(user_id, None)
            captain.team_id = team.id
            await repo.create_player(captain)
            for p in players_payload:
                await repo.create_player(
                    PlayerInfo(
                        id=0,
                        team_id=team.id,
                        user_id=None,  # TEMP 选手不关联账号（user_id 可空）
                        nickname=p["nickname"].strip(),
                        is_captain=0,
                        status="PENDING",
                        player_type="TEMP",
                    )
                )
            team_out = await self._team_out(team)
            return team_out

        team = await repo.create_team(
            TeamInfo(id=0, tournament_id=tournament_id, name=team_name, status=0)
        )
        members[0].team_id = team.id
        await repo.create_player(members[0])
        return await self._team_out(team)

    async def update_team_status(self, user_id: int, team_id: int, status: int) -> dict[str, Any]:
        team = await repo.get_team(team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        await self._require_creator(user_id, team.tournament_id)
        team.status = status
        await repo.update_team(team)
        if status == 1:  # 确认报名：一并同意待确认选手
            for player in await repo.list_players(team_id):
                if player.status == "PENDING":
                    player.status = "AGREED"
                    await repo.update_player(player)
        return await self._team_out(team)

    async def create_team_by_organizer(
        self, user_id: int, tournament_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """办赛者代报名：为赛事添加一支队伍（队员默认已确认）。"""
        t = await self._require_creator(user_id, tournament_id)
        players_payload = payload.get("players") or []
        if t.team_mode == 2:
            name = players_payload[0]["nickname"] if players_payload else "单人参赛"
            member_list: list[tuple[str, bool]] = [(name, True)]
        else:
            name = (payload.get("name") or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="请填写队伍名")
            if len(players_payload) > t.max_team_members:
                raise HTTPException(status_code=400, detail=f"队伍最多 {t.max_team_members} 人")
            # 允许不写队员：队伍先建好，后续再补队员
            member_list = [
                (p["nickname"].strip(), bool(p.get("is_captain")))
                for p in players_payload
                if p["nickname"].strip()
            ]
        if member_list and not any(captain for _, captain in member_list):
            member_list[0] = (member_list[0][0], True)
        team = await repo.create_team(
            TeamInfo(id=0, tournament_id=tournament_id, name=name, status=1)
        )
        for nickname, is_captain in member_list:
            await repo.create_player(
                PlayerInfo(
                    id=0,
                    team_id=team.id,
                    user_id=None,
                    nickname=nickname,
                    is_captain=1 if is_captain else 0,
                    status="AGREED",
                    player_type="TEMP",
                )
            )
        return await self._team_out(team)

    async def add_player(
        self, user_id: int, team_id: int, nickname: str, is_captain: bool = False
    ) -> dict[str, Any]:
        team = await repo.get_team(team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        tournament = await self._get_tournament_or_404(team.tournament_id)
        if tournament.team_mode == 2:
            raise HTTPException(status_code=400, detail="个人赛不能添加队员")
        players = await repo.list_players(team_id)
        if len(players) >= tournament.max_team_members:
            raise HTTPException(status_code=400, detail=f"队伍最多 {tournament.max_team_members} 人")
        await self._require_team_operator(user_id, team, tournament)
        is_creator = tournament.created_by == user_id
        if is_captain:
            await self._demote_captains(team_id)
        player = await repo.create_player(
            PlayerInfo(
                id=0,
                team_id=team_id,
                user_id=None,  # TEMP 选手不关联账号（user_id 可空）
                nickname=nickname.strip(),
                is_captain=1 if is_captain else 0,
                status="AGREED" if is_creator else "PENDING",
                player_type="TEMP",
            )
        )
        return self._player_out(player)

    async def set_captain(self, user_id: int, player_id: int) -> dict[str, Any]:
        """办赛者把指定队员设为队长，同队其他队员降级为普通。"""
        player = await repo.get_player(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="队员不存在")
        team = await repo.get_team(player.team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        await self._require_creator(user_id, team.tournament_id)
        await self._demote_captains(team.id, keep_id=player.id)
        player.is_captain = 1
        await repo.update_player(player)
        return self._player_out(player)

    async def _demote_captains(self, team_id: int, keep_id: int | None = None) -> None:
        for p in await repo.list_players(team_id):
            if p.is_captain == 1 and p.id != keep_id:
                p.is_captain = 0
                await repo.update_player(p)

    async def update_player_status(self, user_id: int, player_id: int, status: str) -> dict[str, Any]:
        player = await repo.get_player(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="选手不存在")
        team = await repo.get_team(player.team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        await self._require_creator(user_id, team.tournament_id)
        player.status = status
        await repo.update_player(player)
        return self._player_out(player)

    async def delete_player(self, user_id: int, player_id: int) -> None:
        player = await repo.get_player(player_id)
        if player is None:
            raise HTTPException(status_code=404, detail="选手不存在")
        team = await repo.get_team(player.team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        tournament = await self._get_tournament_or_404(team.tournament_id)
        await self._require_team_operator(user_id, team, tournament)
        await repo.delete_player(player_id)

    async def delete_team(self, user_id: int, team_id: int) -> None:
        team = await repo.get_team(team_id)
        if team is None:
            raise HTTPException(status_code=404, detail="队伍不存在")
        tournament = await self._get_tournament_or_404(team.tournament_id)
        await self._require_team_operator(user_id, team, tournament)
        await repo.delete_team(team_id)

    async def my_tournaments(self, user_id: int) -> list[dict[str, Any]]:
        tournaments = await repo.list_tournaments_by_user(user_id)
        result = []
        for t in tournaments:
            my_team = await repo.find_team_by_user(t.id, user_id)
            result.append(
                {
                    **_tournament_out(t),
                    "my_team": (await self._team_out(my_team)) if my_team else None,
                    "team_count": await repo.count_teams(t.id),
                }
            )
        return result

    # ---------- 对局管理 ----------
    async def list_schedules(self, tournament_id: int) -> list[dict[str, Any]]:
        schedules = await repo.list_schedules(tournament_id)
        team_names: dict[int, str] = {}
        for team in await repo.list_teams(tournament_id):
            team_names[team.id] = team.name
        phase_names: dict[int, str] = {}
        for phase in await repo.list_phases(tournament_id):
            phase_names[phase.id] = phase.name
        return [
            self._schedule_out(s, team_names, phase_names)
            for s in schedules
        ]

    async def create_schedule(self, user_id: int, tournament_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        await self._require_creator(user_id, tournament_id)
        await self._validate_schedule_refs(tournament_id, payload)
        schedule = ScheduleInfo(
            id=0,
            tournament_id=tournament_id,
            phase_id=payload.get("phase_id"),
            round=payload.get("round", 1),
            round_name=payload.get("round_name"),
            bo=payload.get("bo", 1),
            is_final=1 if payload.get("is_final") else 0,
            home_team_id=payload.get("home_team_id"),
            away_team_id=payload.get("away_team_id"),
            start_time=payload.get("start_time"),
            status=0,
        )
        created = await repo.create_schedule(schedule)
        return self._schedule_out(created, {}, {})

    async def update_schedule(self, user_id: int, schedule_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        schedule = await repo.get_schedule(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="对局不存在")
        await self._require_creator(user_id, schedule.tournament_id)
        await self._validate_schedule_refs(schedule.tournament_id, payload)
        for field in ("phase_id", "round", "round_name", "bo", "home_team_id", "away_team_id", "start_time", "status"):
            if payload.get(field) is not None:
                setattr(schedule, field, payload[field])
        if payload.get("is_final") is not None:
            schedule.is_final = 1 if payload["is_final"] else 0
        if payload.get("home_score") is not None:
            schedule.home_score = payload["home_score"]
        if payload.get("away_score") is not None:
            schedule.away_score = payload["away_score"]
        await repo.update_schedule(schedule)
        return self._schedule_out(schedule, {}, {})

    async def delete_schedule(self, user_id: int, schedule_id: int) -> None:
        schedule = await repo.get_schedule(schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="对局不存在")
        await self._require_creator(user_id, schedule.tournament_id)
        await repo.delete_schedule(schedule_id)

    # ================= 内部工具 =================
    @staticmethod
    def _apply_tournament_fields(t: TournamentInfo, payload: dict[str, Any]) -> None:
        for field in (
            "game", "game_maps", "team_mode", "start_time", "end_time",
            "reg_start_time", "reg_end_time", "max_team_members", "max_teams",
            "regist_method", "contact_requirement", "rule_info",
        ):
            if payload.get(field) is not None:
                setattr(t, field, payload[field])

    @staticmethod
    def _captain_player(user_id: int, nickname: str | None) -> PlayerInfo:
        return PlayerInfo(
            id=0,
            team_id=0,  # 占位，由调用方在创建队伍后赋值
            user_id=user_id,
            nickname=nickname or f"玩家{str(user_id)[-4:]}",
            is_captain=1,
            status="AGREED",
            player_type="REAL",
        )

    async def _list_teams_with_players(self, tournament_id: int) -> list[dict[str, Any]]:
        teams = await repo.list_teams(tournament_id)
        result = []
        for team in teams:
            result.append(await self._team_out(team))
        return result

    async def _team_out(self, team: TeamInfo) -> dict[str, Any]:
        players = await repo.list_players(team.id)
        return {
            "id": team.id,
            "tournament_id": team.tournament_id,
            "name": team.name,
            "status": team.status,
            "status_label": TEAM_STATUS.get(team.status, str(team.status)),
            "created_at": team.created_at,
            "players": [self._player_out(p) for p in players],
            "player_count": len(players),
        }

    @staticmethod
    def _player_out(p: PlayerInfo) -> dict[str, Any]:
        return {
            "id": p.id,
            "team_id": p.team_id,
            "user_id": p.user_id,
            "nickname": p.nickname,
            "is_captain": p.is_captain,
            "status": p.status,
            "player_type": p.player_type,
            "created_at": p.created_at,
        }

    @staticmethod
    def _phase_out(p: TournamentPhaseInfo) -> dict[str, Any]:
        return {
            "id": p.id,
            "tournament_id": p.tournament_id,
            "name": p.name,
            "start_time": p.start_time,
            "end_time": p.end_time,
            "status": p.status,
            "status_label": PHASE_STATUS.get(p.status, str(p.status)),
        }

    @staticmethod
    def _schedule_out(
        s: ScheduleInfo,
        team_names: dict[int, str],
        phase_names: dict[int, str],
    ) -> dict[str, Any]:
        return {
            "id": s.id,
            "tournament_id": s.tournament_id,
            "phase_id": s.phase_id,
            "phase_name": phase_names.get(s.phase_id or -1) or (s.phase_id or ""),
            "round": s.round,
            "round_name": s.round_name,
            "bo": s.bo,
            "is_final": s.is_final,
            "home_team_id": s.home_team_id,
            "home_team_name": team_names.get(s.home_team_id or -1) or "待定",
            "away_team_id": s.away_team_id,
            "away_team_name": team_names.get(s.away_team_id or -1) or "待定",
            "home_score": s.home_score,
            "away_score": s.away_score,
            "status": s.status,
            "status_label": SCHEDULE_STATUS.get(s.status, str(s.status)),
            "start_time": s.start_time,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }

    async def _get_tournament_or_404(self, tournament_id: int) -> TournamentInfo:
        t = await repo.get_tournament(tournament_id)
        if t is None:
            raise HTTPException(status_code=404, detail="赛事不存在")
        return t

    async def _require_creator(self, user_id: int, tournament_id: int) -> TournamentInfo:
        t = await self._get_tournament_or_404(tournament_id)
        if t.created_by != user_id:
            raise HTTPException(status_code=403, detail="只有办赛者可执行该操作")
        return t

    async def _require_team_operator(
        self, user_id: int, team: TeamInfo, tournament: TournamentInfo
    ) -> None:
        if tournament.created_by == user_id:
            return
        players = await repo.list_players(team.id)
        if any(p.user_id == user_id and p.is_captain == 1 for p in players):
            return
        raise HTTPException(status_code=403, detail="只有办赛者或队长可执行该操作")

    async def _creator_nickname(self, user_id: int) -> str:
        user = await repo.get_user(user_id)
        return user.nickname if user else ""

    async def _validate_schedule_refs(self, tournament_id: int, payload: dict[str, Any]) -> None:
        phase_id = payload.get("phase_id")
        if phase_id is not None:
            phase = await repo.get_phase(phase_id)
            if phase is None or phase.tournament_id != tournament_id:
                raise HTTPException(status_code=400, detail="阶段不属于该赛事")
        teams = {t.id for t in await repo.list_teams(tournament_id)}
        for key in ("home_team_id", "away_team_id"):
            team_id = payload.get(key)
            if team_id is not None and team_id not in teams:
                raise HTTPException(status_code=400, detail=f"{key} 队伍不属于该赛事")


tournament_service = TournamentService()
