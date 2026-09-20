/** SSE 事件类型定义（问数 Agent） */

export interface ProgressEvent {
  type: "progress";
  step: string;
  status: "running" | "success" | "error" | "warning";
  message?: string;
  keywords?: string[];
  hits?: { columns: number; metrics: number; values: number };
  rows?: number;
  sql?: string;
  error?: string;
}

export interface DoneEvent {
  type: "done";
  result?: { columns: string[]; rows: Record<string, unknown>[] } | null;
  sql?: string;
  error?: string;
}

export type AgentEvent = ProgressEvent | DoneEvent;

/* ================= 赛事业务域类型 ================= */

export interface User {
  id: number;
  nickname: string;
  phone?: string | null;
  created_at?: string | null;
}

export interface Tournament {
  id: number;
  name: string;
  created_by: number;
  created_by_nickname?: string;
  game?: string | null;
  game_maps?: string | null;
  team_mode: number; // 1团队赛 2个人赛
  start_time?: string | null;
  end_time?: string | null;
  reg_start_time?: string | null;
  reg_end_time?: string | null;
  max_team_members: number;
  max_teams: number;
  regist_method: number; // 1办赛者代报名 2选手自主报名
  contact_requirement?: string | null;
  rule_info?: string | null;
  status: number; // 0草稿 1已发布 2报名中 3比赛中 4已结束
  status_label: string;
  created_at?: string | null;
  updated_at?: string | null;
  team_count?: number;
  player_count?: number;
}

export interface Player {
  id: number;
  team_id: number;
  user_id: number | null;
  nickname: string;
  is_captain: number;
  status: string; // AGREED / PENDING / REJECTED
  player_type: string; // TEMP / REAL
  created_at?: string | null;
}

export interface Team {
  id: number;
  tournament_id: number;
  name: string;
  status: number; // 0待审核 1已确认 2已驳回 3已取消
  status_label: string;
  created_at?: string | null;
  players: Player[];
  player_count: number;
}

export interface Phase {
  id: number;
  tournament_id: number;
  name: string;
  start_time?: string | null;
  end_time?: string | null;
  status: number; // 0未开始 1进行中 2已结束
  status_label: string;
}

export interface Schedule {
  id: number;
  tournament_id: number;
  phase_id: number | null;
  phase_name: string;
  round: number;
  round_name?: string | null;
  bo: number;
  is_final: number;
  home_team_id: number | null;
  home_team_name: string;
  away_team_id: number | null;
  away_team_name: string;
  home_score: number | null;
  away_score: number | null;
  status: number; // 0未开赛 1进行中 2已结束 3已取消
  status_label: string;
  start_time?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TournamentDetail extends Tournament {
  created_by_nickname: string;
  phases: Phase[];
  teams: Team[];
  stats: {
    team_count: number;
    confirmed_team_count: number;
    pending_team_count: number;
    player_count: number;
  };
  my_team: Team | null;
  can_register: boolean;
  is_creator: boolean;
}

export interface MyTournamentItem extends Tournament {
  my_team: Team | null;
  team_count: number;
}
