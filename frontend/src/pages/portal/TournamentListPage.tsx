/** 官网：赛事广场（列表只展示，报名入口在详情页 / 指定链接）。 */

import { useEffect, useState } from "react";
import type { Tournament } from "../../types";
import { tournamentApi } from "../../lib/api";
import TournamentCard from "../../components/TournamentCard";
import { Empty, ErrorBanner, Spinner } from "../../components/ui";

export default function TournamentListPage() {
  const [list, setList] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    tournamentApi
      .list("published")
      .then(setList)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner text="加载赛事列表…" />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">赛事广场</h1>
        <p className="mt-1 text-sm text-gray-500">浏览已发布的赛事，点击进入详情报名</p>
      </div>
      {list.length === 0 ? (
        <Empty text="暂无已发布赛事" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((t) => (
            <TournamentCard key={t.id} tournament={t} />
          ))}
        </div>
      )}
    </div>
  );
}
