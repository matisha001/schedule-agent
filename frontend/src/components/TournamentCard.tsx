/** 赛事卡片：官网列表 / 我的比赛共用。 */

import { Link } from "react-router-dom";
import { Calendar, MapPin, Users } from "lucide-react";
import type { Tournament } from "../types";
import { Badge } from "./ui";
import { formatDate, registMethodLabel, teamModeLabel } from "../lib/format";

export default function TournamentCard({
  tournament,
  footer,
}: {
  tournament: Tournament;
  footer?: React.ReactNode;
}) {
  const t = tournament;
  return (
    <Link
      to={`/tournaments/${t.id}`}
      className="group block rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold group-hover:text-blue-600">{t.name}</h3>
          <p className="mt-1 text-sm text-gray-500">
            {t.game || "未设置游戏"} · {teamModeLabel(t.team_mode)} ·{" "}
            {registMethodLabel(t.regist_method)}
          </p>
        </div>
        <Badge label={t.status_label} status={t.status} />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500">
        <span className="inline-flex items-center gap-1">
          <Calendar className="h-3.5 w-3.5" />
          {formatDate(t.start_time)} ~ {formatDate(t.end_time)}
        </span>
        <span className="inline-flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />
          {t.team_count ?? 0}/{t.max_teams} 队
        </span>
        {t.created_by_nickname && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5" />
            办赛者：{t.created_by_nickname}
          </span>
        )}
      </div>
      {footer}
    </Link>
  );
}
