/** 管理后台：我的赛事（创建 / 删除 / 进入管理）。状态流转在赛事详情页操作。 */

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Link2, Plus, Search, Settings2, Trash2 } from "lucide-react";
import type { Tournament } from "../../types";
import { ApiError, tournamentApi } from "../../lib/api";
import {
  Badge,
  Button,
  Empty,
  ErrorBanner,
  Field,
  Input,
  Modal,
  Select,
  Spinner,
  Textarea,
} from "../../components/ui";
import { alertDialog, confirmDialog } from "../../components/dialog";
import { formatDateTime, registMethodLabel, teamModeLabel } from "../../lib/format";

const EMPTY_FORM = {
  name: "",
  game: "",
  game_maps: "",
  team_mode: 1,
  start_time: "",
  end_time: "",
  reg_start_time: "",
  reg_end_time: "",
  max_team_members: 5,
  max_teams: 16,
  regist_method: 1,
  contact_requirement: "",
  rule_info: "",
};

export default function AdminTournamentsPage() {
  const [list, setList] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    tournamentApi
      .list("mine")
      .then(setList)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (t: Tournament) => {
    if (!(await confirmDialog(`确定删除赛事「${t.name}」吗？其阶段、报名队伍与对局将一并删除，不可恢复。`, { title: "删除确认", danger: true }))) return;
    try {
      await tournamentApi.remove(t.id);
      load();
    } catch (err) {
      await alertDialog(err instanceof ApiError ? err.message : "删除失败", { title: "删除失败" });
    }
  };

  const copyRegLink = (t: Tournament) => {
    const url = `${window.location.origin}/register/${t.id}`;
    navigator.clipboard
      ?.writeText(url)
      .then(() => alertDialog(`报名链接已复制：\n${url}`))
      .catch(() => alertDialog(`复制失败，请手动复制：\n${url}`, { title: "复制失败" }));
  };

  const submitCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      await alertDialog("请填写赛事名称");
      return;
    }
    setSubmitting(true);
    try {
      await tournamentApi.create({
        ...form,
        name: form.name.trim(),
        start_time: form.start_time || null,
        end_time: form.end_time || null,
        reg_start_time: form.reg_start_time || null,
        reg_end_time: form.reg_end_time || null,
      });
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      await alertDialog(err instanceof ApiError ? err.message : "创建失败", { title: "创建失败" });
    } finally {
      setSubmitting(false);
    }
  };

  const set = <K extends keyof typeof EMPTY_FORM>(key: K, value: (typeof EMPTY_FORM)[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const kw = keyword.trim().toLowerCase();
  const filtered = list.filter((t) => {
    if (statusFilter !== "" && t.status !== Number(statusFilter)) return false;
    if (kw && !`${t.name} ${t.game ?? ""}`.toLowerCase().includes(kw)) return false;
    return true;
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">我的赛事</h1>
          <p className="mt-1 text-sm text-gray-500">创建并管理你主办的赛事</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" /> 创建赛事
        </Button>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* 查询工具条：关键词（赛事名/游戏名）+ 状态筛选 */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索赛事名 / 游戏名"
            className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:border-blue-500"
        >
          <option value="">全部状态</option>
          <option value="0">草稿</option>
          <option value="1">已发布</option>
          <option value="2">报名中</option>
          <option value="3">比赛中</option>
          <option value="4">已结束</option>
        </select>
        {filtered.length > 0 && (
          <span className="text-xs text-gray-400">共 {filtered.length} 场赛事</span>
        )}
      </div>

      {loading ? (
        <Spinner text="加载赛事…" />
      ) : filtered.length === 0 ? (
        list.length === 0 ? (
          <Empty text="还没有创建赛事，点击右上角「创建赛事」开始" />
        ) : (
          <Empty text="没有符合条件的赛事，调整搜索或筛选试试" />
        )
      ) : (
        <div className="space-y-3">
          {filtered.map((t) => (
            <div
              key={t.id}
              className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Link to={`/admin/tournaments/${t.id}`} className="text-base font-semibold hover:text-blue-600">
                      {t.name}
                    </Link>
                    <Badge label={t.status_label} status={t.status} />
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    {t.game || "未设置游戏"} · {teamModeLabel(t.team_mode)} ·{" "}
                    {registMethodLabel(t.regist_method)} · {t.team_count ?? 0}/{t.max_teams} 队
                  </p>
                  <p className="mt-1 text-xs text-gray-400">
                    赛事时间：{formatDateTime(t.start_time)} ~ {formatDateTime(t.end_time)}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => copyRegLink(t)}
                    className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600 transition-colors hover:bg-gray-50 hover:text-blue-600"
                    title="复制玩家报名链接，发给选手报名"
                  >
                    <Link2 className="h-3.5 w-3.5" /> 复制报名链接
                  </button>
                  <Link
                    to={`/admin/tournaments/${t.id}`}
                    className="inline-flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-gray-700"
                  >
                    <Settings2 className="h-3.5 w-3.5" /> 管理
                  </Link>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(t)}>
                    <Trash2 className="h-4 w-4 text-red-500" /> 删除
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 创建赛事弹窗 */}
      <Modal
        open={createOpen}
        title="创建赛事"
        onClose={() => setCreateOpen(false)}
        width="max-w-2xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              取消
            </Button>
            <Button onClick={submitCreate} form="create-form" type="submit" loading={submitting}>
              创建（草稿）
            </Button>
          </>
        }
      >
        <form id="create-form" onSubmit={submitCreate} className="grid gap-4 sm:grid-cols-2">
          <Field label="赛事名称" required>
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="例如：秋季争霸赛" maxLength={128} />
          </Field>
          <Field label="游戏项目">
            <Input value={form.game} onChange={(e) => set("game", e.target.value)} placeholder="例如：魔兽争霸3" maxLength={64} />
          </Field>
          <Field label="组队模式">
            <Select value={form.team_mode} onChange={(e) => set("team_mode", Number(e.target.value))}>
              <option value={1}>团队赛</option>
              <option value={2}>个人赛</option>
            </Select>
          </Field>
          <Field label="报名方式">
            <Select value={form.regist_method} onChange={(e) => set("regist_method", Number(e.target.value))}>
              <option value={1}>办赛者代报名</option>
              <option value={2}>选手自主报名</option>
            </Select>
          </Field>
          <Field label="赛事开始时间">
            <Input type="datetime-local" value={form.start_time} onChange={(e) => set("start_time", e.target.value)} />
          </Field>
          <Field label="赛事结束时间">
            <Input type="datetime-local" value={form.end_time} onChange={(e) => set("end_time", e.target.value)} />
          </Field>
          <Field label="报名开始时间">
            <Input type="datetime-local" value={form.reg_start_time} onChange={(e) => set("reg_start_time", e.target.value)} />
          </Field>
          <Field label="报名结束时间">
            <Input type="datetime-local" value={form.reg_end_time} onChange={(e) => set("reg_end_time", e.target.value)} />
          </Field>
          <Field label="队伍最大成员数" hint={form.team_mode === 2 ? "个人赛固定 1 人" : undefined}>
            <Input
              type="number"
              min={1}
              max={50}
              value={form.max_team_members}
              onChange={(e) => set("max_team_members", Number(e.target.value))}
              disabled={form.team_mode === 2}
            />
          </Field>
          <Field label="队伍数量上限" hint="推荐 4/8/16/32 的幂次">
            <Input type="number" min={1} max={4096} value={form.max_teams} onChange={(e) => set("max_teams", Number(e.target.value))} />
          </Field>
          <Field label="可选地图" className="sm:col-span-2">
            <Input value={form.game_maps} onChange={(e) => set("game_maps", e.target.value)} placeholder="地图名，用逗号分隔" maxLength={2000} />
          </Field>
          <Field label="联系方式要求" className="sm:col-span-2">
            <Input value={form.contact_requirement} onChange={(e) => set("contact_requirement", e.target.value)} placeholder="例如：手机号必填，方便赛前联系" maxLength={255} />
          </Field>
          <Field label="比赛规则" className="sm:col-span-2">
            <Textarea rows={4} value={form.rule_info} onChange={(e) => set("rule_info", e.target.value)} placeholder="赛制、晋级规则、注意事项等" maxLength={2000} />
          </Field>
        </form>
      </Modal>
    </div>
  );
}
