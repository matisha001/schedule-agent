/** 管理后台：赛事详情（基础配置 / 报名管理 / 对局管理）。 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Link2 } from "lucide-react";
import type { TournamentDetail } from "../../types";
import { ApiError, tournamentApi } from "../../lib/api";
import { Badge, Button, Empty, ErrorBanner, Spinner } from "../../components/ui";
import BasicConfigTab from "./tabs/BasicConfigTab";
import RegistrationTab from "./tabs/RegistrationTab";
import SchedulesTab from "./tabs/SchedulesTab";

type TabKey = "basic" | "registration" | "schedules";
const TABS: { key: TabKey; label: string }[] = [
  { key: "basic", label: "基础配置" },
  { key: "registration", label: "报名管理" },
  { key: "schedules", label: "对局管理" },
];

export default function AdminTournamentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<TabKey>("basic");

  const load = useCallback(() => {
    if (!id) return;
    setLoading(true);
    tournamentApi
      .detail(id)
      .then((d) => {
        if (!d.is_creator) throw new Error("你不是该赛事的办赛者");
        setDetail(d);
        setError("");
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Spinner text="加载赛事…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!detail) return <Empty />;

  const transition = async (action: string) => {
    try {
      await tournamentApi.transition(detail.id, action);
      load();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/admin"
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
          >
            <ArrowLeft className="h-4 w-4" /> 我的赛事
          </Link>
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            {detail.name}
            <Badge label={detail.status_label} status={detail.status} />
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              navigator.clipboard?.writeText(
                `${window.location.origin}/register/${detail.id}`,
              );
              alert("报名链接已复制，可分享给玩家");
            }}
          >
            <Link2 className="h-3.5 w-3.5" /> 复制报名链接
          </Button>
          {detail.status === 0 && (
            <Button size="sm" onClick={() => transition("publish")}>
              发布赛事
            </Button>
          )}
          {detail.status === 1 && (
            <>
              <Button size="sm" variant="success" onClick={() => transition("open")}>
                开始报名
              </Button>
              <Button size="sm" variant="secondary" onClick={() => transition("start")}>
                直接开赛
              </Button>
            </>
          )}
          {detail.status === 2 && (
            <>
              <Button size="sm" variant="secondary" onClick={() => transition("close")}>
                结束报名
              </Button>
              <Button size="sm" variant="success" onClick={() => transition("start")}>
                开始比赛
              </Button>
            </>
          )}
          {detail.status === 3 && (
            <Button size="sm" onClick={() => transition("finish")}>
              结束比赛
            </Button>
          )}
        </div>
      </div>

      <div className="flex gap-1 rounded-xl border border-gray-200 bg-white p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t.label}
            {t.key === "registration" && detail.stats.pending_team_count > 0 && (
              <span
                className={`ml-1.5 rounded-full px-1.5 py-0.5 text-xs ${
                  tab === t.key ? "bg-white/20" : "bg-amber-100 text-amber-600"
                }`}
              >
                {detail.stats.pending_team_count}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === "basic" && <BasicConfigTab detail={detail} onChanged={load} />}
      {tab === "registration" && (
        <RegistrationTab detail={detail} onChanged={load} />
      )}
      {tab === "schedules" && <SchedulesTab detail={detail} onChanged={load} />}
    </div>
  );
}
