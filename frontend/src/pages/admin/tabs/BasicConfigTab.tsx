/** 基础配置：赛事信息编辑 + 阶段管理。 */

import { useState, type FormEvent } from "react";
import { CalendarClock, Plus, Trash2 } from "lucide-react";
import type { TournamentDetail } from "../../../types";
import { ApiError, tournamentApi } from "../../../lib/api";
import { Button, Field, Input, Select, Textarea } from "../../../components/ui";
import { formatDateTime } from "../../../lib/format";

export default function BasicConfigTab({
  detail,
  onChanged,
}: {
  detail: TournamentDetail;
  onChanged: () => void;
}) {
  const [form, setForm] = useState({
    name: detail.name,
    game: detail.game ?? "",
    game_maps: detail.game_maps ?? "",
    team_mode: detail.team_mode,
    start_time: toLocalInput(detail.start_time),
    end_time: toLocalInput(detail.end_time),
    reg_start_time: toLocalInput(detail.reg_start_time),
    reg_end_time: toLocalInput(detail.reg_end_time),
    max_team_members: detail.max_team_members,
    max_teams: detail.max_teams,
    regist_method: detail.regist_method,
    contact_requirement: detail.contact_requirement ?? "",
    rule_info: detail.rule_info ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [phaseName, setPhaseName] = useState("");
  const [addingPhase, setAddingPhase] = useState(false);

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      alert("请填写赛事名称");
      return;
    }
    setSaving(true);
    try {
      await tournamentApi.update(detail.id, {
        ...form,
        name: form.name.trim(),
        start_time: form.start_time || null,
        end_time: form.end_time || null,
        reg_start_time: form.reg_start_time || null,
        reg_end_time: form.reg_end_time || null,
      });
      alert("已保存");
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const addPhase = async () => {
    if (!phaseName.trim()) return;
    try {
      await tournamentApi.createPhase(detail.id, { name: phaseName.trim() });
      setPhaseName("");
      setAddingPhase(false);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "添加失败");
    }
  };

  const removePhase = async (phaseId: number, phaseName: string) => {
    if (!window.confirm(`删除阶段「${phaseName}」？其下的对局也将被删除。`)) return;
    try {
      await tournamentApi.removePhase(phaseId);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "删除失败");
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {/* 赛事信息 */}
      <form
        onSubmit={save}
        className="space-y-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2"
      >
        <h2 className="text-base font-semibold">赛事信息</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="赛事名称" required>
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} maxLength={128} />
          </Field>
          <Field label="游戏项目">
            <Input value={form.game} onChange={(e) => set("game", e.target.value)} maxLength={64} />
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
          <Field label="队伍最大成员数">
            <Input
              type="number"
              min={1}
              max={50}
              value={form.max_team_members}
              onChange={(e) => set("max_team_members", Number(e.target.value))}
              disabled={form.team_mode === 2}
            />
          </Field>
          <Field label="队伍数量上限">
            <Input type="number" min={1} max={4096} value={form.max_teams} onChange={(e) => set("max_teams", Number(e.target.value))} />
          </Field>
          <Field label="可选地图" className="sm:col-span-2">
            <Input value={form.game_maps} onChange={(e) => set("game_maps", e.target.value)} maxLength={2000} />
          </Field>
          <Field label="联系方式要求" className="sm:col-span-2">
            <Input value={form.contact_requirement} onChange={(e) => set("contact_requirement", e.target.value)} maxLength={255} />
          </Field>
          <Field label="比赛规则" className="sm:col-span-2">
            <Textarea rows={5} value={form.rule_info} onChange={(e) => set("rule_info", e.target.value)} maxLength={2000} />
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="submit" loading={saving}>
            保存配置
          </Button>
        </div>
      </form>

      {/* 阶段管理 */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-base font-semibold">
            <CalendarClock className="h-4 w-4 text-gray-400" /> 赛程阶段
          </h2>
          <Button size="sm" variant="secondary" onClick={() => setAddingPhase(true)}>
            <Plus className="h-3.5 w-3.5" /> 添加阶段
          </Button>
        </div>
        {detail.phases.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-400">
            暂无阶段，添加后可在「对局管理」编排对局
          </p>
        )}
        <ul className="space-y-2">
          {detail.phases.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-xl border border-gray-100 px-3 py-2.5"
            >
              <div>
                <p className="text-sm font-medium">{p.name}</p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {formatDateTime(p.start_time)} ~ {formatDateTime(p.end_time)}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => removePhase(p.id, p.name)}>
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </li>
          ))}
        </ul>
        {addingPhase && (
          <div className="mt-3 space-y-2 rounded-xl bg-gray-50 p-3">
            <Input
              value={phaseName}
              onChange={(e) => setPhaseName(e.target.value)}
              placeholder="阶段名称，例如：初赛 / 淘汰赛 / 总决赛"
              maxLength={32}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="ghost" onClick={() => setAddingPhase(false)}>
                取消
              </Button>
              <Button size="sm" onClick={addPhase}>
                添加
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** ISO 时间 → datetime-local 输入框值 */
function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
