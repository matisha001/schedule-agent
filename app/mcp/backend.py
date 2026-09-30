"""赛事后端 HTTP 客户端：把 FastAPI 接口封装为可复用的异步方法。

- MCP 服务强制鉴权：必须配置 API_TOKEN（TOURNAMENT_API_TOKEN），
  未配置时所有请求直接拒绝，不提供游客访问。
"""

from __future__ import annotations

from typing import Any

import httpx


class TournamentBackend:
    def __init__(self, base_url: str = "http://localhost:8000", token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        if not self.token:
            raise ValueError(
                "MCP 服务强制要求 API_TOKEN：请在后端登录接口获取 token 并配置环境变量 "
                "TOURNAMENT_API_TOKEN（见根目录 .env.example）"
            )

    # ---------- 基础 ----------

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self.token:
            raise RuntimeError("未配置 TOURNAMENT_API_TOKEN，无法调用后端接口")
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code >= 400:
                detail = resp.text
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    pass
                raise RuntimeError(f"后端请求失败 {method} {path} → HTTP {resp.status_code}: {detail}")
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()

    # ---------- 认证 / 用户资料 ----------

    async def me(self) -> dict:
        return {"user": await self._request("GET", "/api/auth/me")}

    async def update_profile(self, nickname: str) -> dict:
        """修改当前用户昵称。"""
        return await self._request("PATCH", "/api/auth/profile", json={"nickname": nickname})

    async def update_password(self, old_password: str, new_password: str) -> dict:
        """修改当前用户密码（需校验旧密码）。"""
        return await self._request(
            "PATCH",
            "/api/auth/password",
            json={"old_password": old_password, "new_password": new_password},
        )

    # ---------- 赛事 ----------

    async def list_tournaments(self, scope: str = "published") -> list:
        return await self._request("GET", f"/api/tournaments?scope={scope}")

    async def get_tournament(self, tournament_id: int) -> dict:
        return await self._request("GET", f"/api/tournaments/{tournament_id}")

    async def list_phases(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/phases")

    async def create_tournament(self, payload: dict) -> dict:
        return await self._request("POST", "/api/tournaments", json=payload)

    async def transition_tournament(self, tournament_id: int, action: str) -> dict:
        return await self._request(
            "POST", f"/api/tournaments/{tournament_id}/transition", json={"action": action}
        )

    async def create_phase(self, tournament_id: int, payload: dict) -> dict:
        return await self._request("POST", f"/api/tournaments/{tournament_id}/phases", json=payload)

    # ---------- 报名 ----------

    async def list_teams(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/teams")

    async def my_tournaments(self) -> list:
        return await self._request("GET", "/api/me/tournaments")

    async def register_team(self, tournament_id: int, payload: dict) -> dict:
        """选手自主报名（需登录；办赛者不能报名自己创建的赛事）。"""
        return await self._request("POST", f"/api/tournaments/{tournament_id}/teams", json=payload)

    async def register_team_by_organizer(self, tournament_id: int, payload: dict) -> dict:
        """办赛者代报名（需办赛者本人创建的赛事）。"""
        return await self._request("POST", f"/api/tournaments/{tournament_id}/admin-teams", json=payload)

    async def review_team(self, team_id: int, status: int) -> dict:
        """队伍审核：0待审核 1已确认 2已驳回 3已取消。"""
        return await self._request("PATCH", f"/api/teams/{team_id}/status", json={"status": status})

    # ---------- 赛程 ----------

    async def list_schedules(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/schedules")

    async def create_schedule(self, tournament_id: int, payload: dict) -> dict:
        return await self._request("POST", f"/api/tournaments/{tournament_id}/schedules", json=payload)

    async def update_schedule(self, schedule_id: int, payload: dict) -> dict:
        return await self._request("PATCH", f"/api/schedules/{schedule_id}", json=payload)

    # ---------- 预制提示词 ----------

    async def list_presets(self) -> list:
        return await self._request("GET", "/api/query/presets")
