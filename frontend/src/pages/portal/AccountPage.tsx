/** 账号设置页：修改昵称 / 修改密码 / 申请办赛（玩家）/ 注销账号。 */

import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, LogOut, ShieldCheck, UserCog } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { applyApi, authApi, ApiError, setToken } from "../../lib/api";
import type { OrganizerApplication } from "../../types";
import { APPLICATION_STATUS_LABELS, ROLE_LABELS } from "../../types";
import { Button, ErrorBanner, Field, Input, Spinner, Textarea } from "../../components/ui";

export default function AccountPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [nickname, setNickname] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [reason, setReason] = useState("");
  const [application, setApplication] = useState<OrganizerApplication | null | undefined>(undefined);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [logoutConfirm, setLogoutConfirm] = useState(false);

  useEffect(() => {
    if (user) setNickname(user.nickname);
    if (user?.role === "player") {
      applyApi
        .myStatus()
        .then(setApplication)
        .catch(() => setApplication(null));
    }
  }, [user?.id]);

  if (!user) return <Spinner text="加载用户信息…" />;

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const name = nickname.trim();
    if (!name) {
      setError("昵称不能为空");
      return;
    }
    setSaving(true);
    try {
      await authApi.updateProfile(name);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (oldPassword.length < 6 || newPassword.length < 6) {
      setError("密码长度需为 6-64 位");
      return;
    }
    setSaving(true);
    try {
      await authApi.updatePassword(oldPassword, newPassword);
      setOldPassword("");
      setNewPassword("");
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "修改失败");
    } finally {
      setSaving(false);
    }
  };

  const submitApply = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const app = await applyApi.applyOrganizer(reason.trim());
      setApplication(app);
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "申请失败");
    } finally {
      setSaving(false);
    }
  };

  const deleteAccount = async () => {
    setError("");
    setSaving(true);
    try {
      await authApi.deleteAccount();
      setToken(null);
      logout();
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "注销失败");
    } finally {
      setSaving(false);
    }
  };

  const isPlayer = user.role === "player";
  const appStatus = application ? APPLICATION_STATUS_LABELS[application.status] ?? application.status : null;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header>
        <h1 className="text-xl font-semibold text-gray-900">账号设置</h1>
        <p className="mt-1 text-sm text-gray-500">
          当前角色：{ROLE_LABELS[user.role ?? "player"] ?? user.role}
        </p>
      </header>

      {error && <ErrorBanner message={error} />}

      {/* 昵称 */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-800">
          <UserCog className="h-4 w-4 text-blue-600" /> 修改昵称
        </h2>
        <form onSubmit={saveProfile} className="space-y-3">
          <Field label="昵称">
            <Input value={nickname} maxLength={64} onChange={(e) => setNickname(e.target.value)} />
          </Field>
          <Button type="submit" loading={saving} size="sm">
            保存昵称
          </Button>
        </form>
      </section>

      {/* 密码 */}
      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-800">
          <KeyRound className="h-4 w-4 text-blue-600" /> 修改密码
        </h2>
        <form onSubmit={changePassword} className="space-y-3">
          <Field label="当前密码">
            <Input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="请输入当前密码"
            />
          </Field>
          <Field label="新密码">
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="6-64 位新密码"
            />
          </Field>
          <Button type="submit" loading={saving} size="sm">
            修改密码
          </Button>
        </form>
      </section>

      {/* 申请办赛（仅玩家） */}
      {isPlayer && (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-800">
            <ShieldCheck className="h-4 w-4 text-blue-600" /> 申请成为办赛者
          </h2>
          {application === undefined ? (
            <Spinner text="查询申请状态…" />
          ) : application ? (
            <div className="text-sm text-gray-600">
              当前申请状态：
              <span
                className={`ml-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                  application.status === "APPROVED"
                    ? "bg-emerald-50 text-emerald-700"
                    : application.status === "REJECTED"
                      ? "bg-red-50 text-red-600"
                      : "bg-amber-50 text-amber-700"
                }`}
              >
                {appStatus}
              </span>
              {application.status === "PENDING" && (
                <p className="mt-2 text-xs text-gray-400">提交后由管理员/运营审批，通过后自动升级为办赛者</p>
              )}
              {application.status === "REJECTED" && (
                <p className="mt-2 text-xs text-gray-400">申请被驳回，可重新提交申请</p>
              )}
            </div>
          ) : (
            <form onSubmit={submitApply} className="space-y-3">
              <Field label="申请原因" hint="简要说明办赛目的，提交后由管理员/运营审批">
                <Textarea
                  rows={3}
                  value={reason}
                  maxLength={255}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="例如：希望举办 XX 游戏月赛"
                />
              </Field>
              <Button type="submit" loading={saving} size="sm">
                提交申请
              </Button>
            </form>
          )}
        </section>
      )}

      {/* 注销 */}
      <section className="rounded-2xl border border-red-200 bg-red-50/40 p-5">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-red-700">
          <LogOut className="h-4 w-4" /> 注销账号
        </h2>
        <p className="mb-3 text-xs text-red-500">
          注销后账号无法再登录，历史赛事与报名数据将保留。此操作不可恢复。
        </p>
        {logoutConfirm ? (
          <div className="flex items-center gap-2">
            <Button variant="danger" size="sm" loading={saving} onClick={deleteAccount}>
              确认注销
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setLogoutConfirm(false)}>
              取消
            </Button>
          </div>
        ) : (
          <Button variant="danger" size="sm" onClick={() => setLogoutConfirm(true)}>
            注销账号
          </Button>
        )}
      </section>
    </div>
  );
}
