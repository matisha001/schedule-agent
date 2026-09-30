/** 官网：赛事详情。报名入口在详情页与报名链接（列表不提供报名）。 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Calendar,
  CalendarClock,
  Link2,
  ScrollText,
  ShieldAlert,
  Users,
} from "lucide-react";
import type { Schedule, TournamentDetail } from "../../types";
import { tournamentApi } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import {
  Badge,
  Button,
  Empty,
  ErrorBanner,
  Spinner,
} from "../../components/ui";
import { alertDialog } from "../../components/dialog";
import RegisterTeamModal from "./RegisterTeamModal";
import { formatDateTime, registMethodLabel, teamModeLabel } from "../../lib/format";

export default function TournamentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [registerOpen, setRegisterOpen] = useState(false);

  // 报名链接直达：/register/:id（或 ?register=1）→ 进入页面时自动打开报名弹窗（仅首次）
  const isRegisterLink = location.pathname.startsWith("/register");
  const autoOpenRegister = useRef(
    isRegisterLink || new URLSearchParams(location.search).get("register") === "1",
  );

  useEffect(() => {
    if (autoOpenRegister.current) {
      setRegisterOpen(true);
      autoOpenRegister.current = false;
    }
  }, []);

  const load = useCallback(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([tournamentApi.detail(id), tournamentApi.schedules(Number(id))])
      .then(([d, s]) => {
        setDetail(d);
        setSchedules(s);
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const openRegister = () => {
    if (!user) {
      navigate("/login", { state: { from: `/register/${id}` } });
      return;
    }
    setRegisterOpen(true);
  };

  // 对局按阶段分组（顺序遵循赛事阶段配置，未分阶段的归入「未分阶段」）
  const scheduleSections = useMemo(() => {
    const map = new Map<number, Schedule[]>();
    for (const s of schedules) {
      const key = s.phase_id ?? -1;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    }
    const result: { id: number; name: string; list: Schedule[] }[] = [];
    if (detail) {
      for (const p of detail.phases) {
        if (map.has(p.id)) result.push({ id: p.id, name: p.name, list: map.get(p.id)! });
      }
    }
    if (map.has(-1)) result.push({ id: -1, name: "未分阶段", list: map.get(-1)! });
    return result;
  }, [schedules, detail]);

  if (loading) return <Spinner text="加载赛事详情…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!detail) return <Empty />;

  const regOpen =
    detail.status === 2 && !detail.my_team;

  return (
    <div className="space-y-5">
      {/* 头部 */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{detail.name}</h1>
              <Badge label={detail.status_label} status={detail.status} />
            </div>
            <p className="mt-1.5 text-sm text-gray-500">
              {detail.game || "未设置游戏"} · {teamModeLabel(detail.team_mode)} ·{" "}
              {registMethodLabel(detail.regist_method)} · 办赛者：
              {detail.created_by_nickname}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={async () => {
                await navigator.clipboard?.writeText(
                  `${window.location.origin}/register/${detail.id}`,
                );
                await alertDialog("报名链接已复制，可分享给玩家", { title: "复制成功" });
              }}
            >
              <Link2 className="h-3.5 w-3.5" /> 复制报名链接
            </Button>
            {detail.can_register || (!user && regOpen) ? (
              <Button onClick={openRegister}>立即报名</Button>
            ) : null}
          </div>
        </div>

        <div className="mt-4 grid gap-3 rounded-xl bg-gray-50 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs text-gray-400">赛事时间</p>
            <p className="mt-0.5">{formatDateTime(detail.start_time)} ~ {formatDateTime(detail.end_time)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">报名时间</p>
            <p className="mt-0.5">{formatDateTime(detail.reg_start_time)} ~ {formatDateTime(detail.reg_end_time)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">队伍规模</p>
            <p className="mt-0.5">
              {detail.team_mode === 2 ? "个人参赛" : `每队最多 ${detail.max_team_members} 人`} · 上限 {detail.max_teams} 队
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400">报名进度</p>
            <p className="mt-0.5">
              {detail.stats.team_count}/{detail.max_teams} 队 ·{" "}
              {detail.stats.player_count} 人
            </p>
          </div>
        </div>

        {/* 我的报名状态 */}
        {detail.my_team ? (
          <div className="mt-4 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm">
            <div className="flex items-center gap-2 text-emerald-700">
              <Users className="h-4 w-4" />
              你已报名「{detail.my_team.name}」
              <Badge
                label={detail.my_team.status_label}
                status={detail.my_team.status}
                kind="team"
              />
            </div>
            <Link to="/my" className="text-sm text-blue-600 hover:underline">
              查看我的比赛
            </Link>
          </div>
        ) : regOpen ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">
            <Calendar className="h-4 w-4" /> 报名进行中，创建你的队伍加入赛事
          </div>
        ) : detail.regist_method === 1 ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <ShieldAlert className="h-4 w-4" /> 本赛事由办赛者代报名，如有意参赛请联系办赛者
          </div>
        ) : detail.status !== 2 ? (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-500">
            <Calendar className="h-4 w-4" /> 当前不在报名时间内
          </div>
        ) : null}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* 赛事信息 */}
        <div className="space-y-5">
          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 text-base font-semibold">赛事信息</h2>
            <dl className="space-y-2.5 text-sm">
              <div className="flex gap-3">
                <dt className="w-20 shrink-0 text-gray-400">可选地图</dt>
                <dd className="text-gray-700">{detail.game_maps || "-"}</dd>
              </div>
              <div className="flex gap-3">
                <dt className="w-20 shrink-0 text-gray-400">比赛规则</dt>
                <dd className="whitespace-pre-wrap text-gray-700">{detail.rule_info || "-"}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 flex items-center gap-1.5 text-base font-semibold">
              <ScrollText className="h-4 w-4 text-gray-400" /> 赛程阶段
            </h2>
            {detail.phases.length === 0 ? (
              <Empty text="暂未配置赛程阶段" />
            ) : (
              <ul className="divide-y divide-gray-100 text-sm">
                {detail.phases.map((p) => (
                  <li key={p.id} className="flex items-center justify-between py-2.5">
                    <span className="font-medium">{p.name}</span>
                    <span className="text-gray-400">
                      {formatDateTime(p.start_time)} ~ {formatDateTime(p.end_time)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* 报名队伍 */}
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 flex items-center gap-1.5 text-base font-semibold">
            <Users className="h-4 w-4 text-gray-400" /> 报名队伍
            <span className="text-xs font-normal text-gray-400">
              {detail.stats.team_count} 队
            </span>
          </h2>
          {detail.teams.length === 0 ? (
            <Empty text="暂无队伍报名" />
          ) : (
            <ul className="space-y-2">
              {detail.teams.map((team) => (
                <li
                  key={team.id}
                  className="flex items-center justify-between rounded-xl border border-gray-100 px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">
                      {team.name}
                      <Badge label={team.status_label} status={team.status} kind="team" />
                    </p>
                    <p className="mt-0.5 text-xs text-gray-400">
                      {team.players.map((p) => p.nickname).join("、") || "—"}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400">{team.player_count} 人</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* 对局赛程 */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 flex items-center gap-1.5 text-base font-semibold">
          <CalendarClock className="h-4 w-4 text-gray-400" /> 对局赛程
          <span className="text-xs font-normal text-gray-400">{schedules.length} 场</span>
        </h2>
        {schedules.length === 0 ? (
          <Empty text="暂无对局" />
        ) : (
          <div className="space-y-4">
            {scheduleSections.map(({ id, name, list }) => (
              <div key={id}>
                <p className="mb-1.5 text-sm font-medium text-gray-500">
                  {name} <span className="text-xs font-normal text-gray-400">{list.length} 场</span>
                </p>
                <ul className="divide-y divide-gray-100 rounded-xl border border-gray-100">
                  {list.map((s) => (
                    <li
                      key={s.id}
                      className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="shrink-0 text-sm text-gray-400">
                          {s.round_name || `第${s.round}轮`}
                          {s.is_final === 1 && (
                            <span className="ml-1 text-blue-600">决赛</span>
                          )}
                        </span>
                        <div className="flex items-center gap-2 text-sm font-medium">
                          <span className="truncate">{s.home_team_name}</span>
                          <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
                            {s.status === 2
                              ? `${s.home_score ?? 0} : ${s.away_score ?? 0}`
                              : "vs"}
                          </span>
                          <span className="truncate">{s.away_team_name}</span>
                        </div>
                        <Badge label={s.status_label} status={s.status} kind="schedule" />
                      </div>
                      <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                        <CalendarClock className="h-3.5 w-3.5" />
                        {formatDateTime(s.start_time)}
                        <span className="text-gray-300">|</span> BO{s.bo}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      <RegisterTeamModal
        detail={detail}
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onSuccess={() => {
          setRegisterOpen(false);
          load();
        }}
      />
    </div>
  );
}
