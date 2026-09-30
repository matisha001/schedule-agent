"""赛事后端 HTTP 客户端：把 FastAPI 接口封装为可复用的异步方法。

- 统一携带 Authorization: Bearer <token>（若配置了登录 token）
"""

from __future__ import annotations

from typing import Any

import httpx


class TournamentBackend:
    def __init__(self, base_url: str = "http://localhost:8000", token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token

    # ---------- 基础 ----------

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
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

    # ---------- 认证 ----------

    async def me(self) -> dict:
        if not self.token:
            return {"login": False, "message": "未登录（游客模式）。可通过环境变量 TOURNAMENT_API_TOKEN 注入登录 token 获得完整权限。"}
        return {"login": True, "user": await self._request("GET", "/api/auth/me")}

    # ---------- 赛事 ----------

    async def list_tournaments(self, scope: str = "published") -> list:
        return await self._request("GET", f"/api/tournaments?scope={scope}")

    async def get_tournament(self, tournament_id: int) -> dict:
        return await self._request("GET", f"/api/tournaments/{tournament_id}")

    async def list_phases(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/phases")

    # ---------- 报名 ----------

    async def list_teams(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/teams")

    async def my_tournaments(self) -> list:
        return await self._request("GET", "/api/me/tournaments")

    # ---------- 赛程 ----------

    async def list_schedules(self, tournament_id: int) -> list:
        return await self._request("GET", f"/api/tournaments/{tournament_id}/schedules")

    # ---------- 预制提示词 ----------

    async def list_presets(self) -> list:
        return await self._request("GET", "/api/query/presets")
