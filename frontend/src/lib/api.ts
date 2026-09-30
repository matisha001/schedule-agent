/** 业务 API 客户端：统一鉴权头、JSON 编解码与错误处理。 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean; // 默认 true：附带 token
  signal?: AbortSignal;
}

export async function api<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, auth = true, signal } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (response.status === 204) return undefined as T;

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `请求失败（HTTP ${response.status}）`;
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export const authApi = {
  login: (phone: string, password: string) =>
    api<{ token: string; user: import("../types").User }>("/api/auth/login", {
      method: "POST",
      body: { phone, password },
      auth: false,
    }),
  me: () => api<import("../types").User>("/api/auth/me"),
};

export const tournamentApi = {
  list: (scope: "published" | "mine") =>
    api<import("../types").Tournament[]>(`/api/tournaments?scope=${scope}`),
  detail: (id: number | string) =>
    api<import("../types").TournamentDetail>(`/api/tournaments/${id}`),
  create: (data: Record<string, unknown>) =>
    api<import("../types").Tournament>("/api/tournaments", { method: "POST", body: data }),
  update: (id: number, data: Record<string, unknown>) =>
    api<import("../types").Tournament>(`/api/tournaments/${id}`, { method: "PUT", body: data }),
  remove: (id: number) => api<void>(`/api/tournaments/${id}`, { method: "DELETE" }),
  transition: (id: number, action: string) =>
    api<import("../types").Tournament>(`/api/tournaments/${id}/transition`, {
      method: "POST",
      body: { action },
    }),
  phases: (id: number) =>
    api<import("../types").Phase[]>(`/api/tournaments/${id}/phases`),
  createPhase: (id: number, data: Record<string, unknown>) =>
    api<import("../types").Phase>(`/api/tournaments/${id}/phases`, {
      method: "POST",
      body: data,
    }),
  updatePhase: (phaseId: number, data: Record<string, unknown>) =>
    api<import("../types").Phase>(`/api/tournaments/phases/${phaseId}`, {
      method: "PUT",
      body: data,
    }),
  removePhase: (phaseId: number) =>
    api<void>(`/api/tournaments/phases/${phaseId}`, { method: "DELETE" }),
  teams: (id: number) =>
    api<import("../types").Team[]>(`/api/tournaments/${id}/teams`),
  createTeam: (id: number, data: Record<string, unknown>) =>
    api<import("../types").Team>(`/api/tournaments/${id}/teams`, {
      method: "POST",
      body: data,
    }),
  createTeamByOrganizer: (id: number, data: Record<string, unknown>) =>
    api<import("../types").Team>(`/api/tournaments/${id}/admin-teams`, {
      method: "POST",
      body: data,
    }),
  teamStatus: (teamId: number, status: number) =>
    api<import("../types").Team>(`/api/teams/${teamId}/status`, {
      method: "PATCH",
      body: { status },
    }),
  removeTeam: (teamId: number) => api<void>(`/api/teams/${teamId}`, { method: "DELETE" }),
  addPlayer: (teamId: number, nickname: string, isCaptain = false) =>
    api<import("../types").Player>(`/api/teams/${teamId}/players`, {
      method: "POST",
      body: { nickname, is_captain: isCaptain },
    }),
  setCaptain: (playerId: number) =>
    api<import("../types").Player>(`/api/players/${playerId}/captain`, { method: "PATCH" }),
  playerStatus: (playerId: number, status: string) =>
    api<import("../types").Player>(`/api/players/${playerId}/status`, {
      method: "PATCH",
      body: { status },
    }),
  removePlayer: (playerId: number) =>
    api<void>(`/api/players/${playerId}`, { method: "DELETE" }),
  myTournaments: () =>
    api<import("../types").MyTournamentItem[]>("/api/me/tournaments"),
  schedules: (id: number) =>
    api<import("../types").Schedule[]>(`/api/tournaments/${id}/schedules`),
  createSchedule: (id: number, data: Record<string, unknown>) =>
    api<import("../types").Schedule>(`/api/tournaments/${id}/schedules`, {
      method: "POST",
      body: data,
    }),
  updateSchedule: (scheduleId: number, data: Record<string, unknown>) =>
    api<import("../types").Schedule>(`/api/schedules/${scheduleId}`, {
      method: "PATCH",
      body: data,
    }),
  removeSchedule: (scheduleId: number) =>
    api<void>(`/api/schedules/${scheduleId}`, { method: "DELETE" }),
};
