/** 后台用户权限管理（仅超级管理员）：分页列表 + 角色调整。 */

import { useCallback, useEffect, useState } from "react";
import { Shield, UserCog } from "lucide-react";
import type { AdminUser } from "../../types";
import { ROLE_LABELS, ROLE_OPTIONS } from "../../types";
import { adminApi, ApiError } from "../../lib/api";
import { Button, Empty, ErrorBanner, Select, Spinner } from "../../components/ui";
import { formatDateTime } from "../../lib/format";

const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const [items, setItems] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const load = useCallback((p: number) => {
    setLoading(true);
    setError("");
    adminApi
      .users(p, PAGE_SIZE)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setPage(data.page);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(1);
  }, [load]);

  const changeRole = async (user: AdminUser, role: string) => {
    if (role === user.role) return;
    setUpdatingId(user.id);
    setError("");
    try {
      await adminApi.updateRole(user.id, role);
      await load(page);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改角色失败");
    } finally {
      setUpdatingId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Shield className="h-5 w-5 text-blue-600" /> 用户权限管理
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            调整用户角色以控制其可查询与可操作的权限范围（共 {total} 个用户）
          </p>
        </div>
      </header>

      {error && <ErrorBanner message={error} />}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
        {loading ? (
          <Spinner text="加载用户列表…" />
        ) : items.length === 0 ? (
          <Empty text="暂无用户" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs text-gray-500">
                <th className="px-4 py-3 font-medium">用户</th>
                <th className="px-4 py-3 font-medium">手机号</th>
                <th className="px-4 py-3 font-medium">当前角色</th>
                <th className="px-4 py-3 font-medium">注册时间</th>
                <th className="px-4 py-3 font-medium">调整角色</th>
              </tr>
            </thead>
            <tbody>
              {items.map((u) => (
                <tr key={u.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/60">
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2 font-medium text-gray-800">
                      <UserCog className="h-4 w-4 text-gray-400" />
                      {u.nickname}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{u.phone ?? "-"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.role === "super_admin"
                          ? "bg-amber-50 text-amber-700"
                          : u.role === "organizer"
                            ? "bg-blue-50 text-blue-700"
                            : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {ROLE_LABELS[u.role] ?? u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {u.created_at ? formatDateTime(u.created_at) : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      value={u.role}
                      disabled={updatingId === u.id}
                      onChange={(e) => changeRole(u, e.target.value)}
                      className="w-40 py-1.5 text-xs"
                    >
                      {ROLE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </Select>
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
            第 {page} / {totalPages} 页 · 共 {total} 人
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => load(page - 1)}
            >
              上一页
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => load(page + 1)}
            >
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
