/** 官网：我的比赛（玩家报名参加过的赛事 + 我的队伍与状态）。 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { MyTournamentItem } from "../../types";
import { tournamentApi } from "../../lib/api";
import { Badge, Empty, ErrorBanner, Spinner } from "../../components/ui";
import { formatDate } from "../../lib/format";

export default function MyTournamentsPage() {
  const [list, setList] = useState<MyTournamentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    tournamentApi
      .myTournaments()
      .then(setList)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner text="加载我的比赛…" />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">我的比赛</h1>
        <p className="mt-1 text-sm text-gray-500">你报名参加过的全部赛事</p>
      </div>
      {list.length === 0 ? (
        <Empty text="还没有报名任何赛事，去赛事广场逛逛吧" />
      ) : (
        <div className="space-y-3">
          {list.map((t) => (
            <Link
              key={t.id}
              to={`/tournaments/${t.id}`}
              className="flex items-center justify-between rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition-colors hover:border-blue-200"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-semibold">{t.name}</h3>
                  <Badge label={t.status_label} status={t.status} />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {formatDate(t.start_time)} ~ {formatDate(t.end_time)} · {t.team_count} 队参赛
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">
                  {t.my_team?.name ?? "-"}
                  {t.my_team && (
                    <Badge
                      label={t.my_team.status_label}
                      status={t.my_team.status}
                      kind="team"
                    />
                  )}
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  {t.my_team?.players.map((p) => p.nickname).join("、") || ""}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
