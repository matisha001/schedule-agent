/** 办赛申请审批（超管/运营）：查看申请人+原因，点通过/驳回即完成并记录。 */

import { useCallback, useEffect, useState } from "react";
import { Check, ClipboardList, X } from "lucide-react";
import type { OrganizerApplication } from "../../types";
import { APPLICATION_STATUS_LABELS } from "../../types";
import { adminApi, ApiError } from "../../lib/api";
import { Button, Empty, ErrorBanner, Select, Spinner } from "../../components/ui";
import { formatDateTime } from "../../lib/format";

const PAGE_SIZE = 20;
const FILTERS = [
  { value: "", label: "全部" },
  { value: "PENDING", label: "待审批" },
  { value: "APPROVED", label: "已通过" },
  { value: "REJECTED", label: "已驳回" },
];

const STATUS_STYLE: Record<string, string> = {
  PENDING: "bg-amber-50 text-amber-700",
  APPROVED: "bg-emerald-50 text-emerald-700",
  REJECTED: "bg-red-50 text-red-600",
};

export default function AdminApplicationsPage() {
  const [items, setItems] = useState<OrganizerApplication[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("PENDING");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [operatingId, setOperatingId] = useState<number | null>(null);

  const load = useCallback((p: number, st: string) => {
    setLoading(true);
    setError("");
    adminApi
      .applications(st || undefined, p, PAGE_SIZE)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setPage(data.page);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(1, status);
  }, [load, status]);

  const review = async (id: number, approve: boolean) => {
    setOperatingId(id);
    setError("");
    try {
      await adminApi.reviewApplication(id, approve);
      await load(page, status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setOperatingId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <ClipboardList className="h-5 w-5 text-blue-600" /> 办赛申请审批
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            玩家申请成为办赛者 · 通过后自动升级 · 共 {total} 条
          </p>
          <div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-36">
          {FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </Select>
          </div>
        </div>
      
      </header>

      {error && <ErrorBanner message={error} />}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <Spinner text="加载申请列表…" />
        ) : items.length === 0 ? (
          <Empty text={status ? `暂无「${FILTERS.find((f) => f.value === status)?.label}」申请` : "暂无申请"} />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs text-gray-500">
                <th className="px-4 py-3 font-medium">申请人</th>
                <th className="px-4 py-3 font-medium">申请原因</th>
                <th className="px-4 py-3 font-medium">申请时间</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/60">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-800">{a.nickname || `用户${a.user_id}`}</div>
                    <div className="text-xs text-gray-400">ID: {a.user_id}</div>
                  </td>
                  <td className="max-w-[260px] px-4 py-3 text-gray-600">
                    {a.reason || <span className="text-gray-300">（未填写）</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{a.created_at ? formatDateTime(a.created_at) : "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[a.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {APPLICATION_STATUS_LABELS[a.status] ?? a.status}
                    </span>
                    {a.reviewed_at && (
                      <div className="mt-0.5 text-xs text-gray-400">审批：{formatDateTime(a.reviewed_at)}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {a.status === "PENDING" ? (
                      <div className="flex gap-2">
                        <Button
                          variant="success"
                          size="sm"
                          loading={operatingId === a.id}
                          onClick={() => review(a.id, true)}
                        >
                          <Check className="h-3.5 w-3.5" /> 通过
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          loading={operatingId === a.id}
                          onClick={() => review(a.id, false)}
                        >
                          <X className="h-3.5 w-3.5" /> 驳回
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">已处理</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            第 {page} / {totalPages} 页
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => load(page - 1, status)}>
              上一页
            </Button>
            <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => load(page + 1, status)}>
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
