/** 对局管理：按阶段编排对局、设置开赛时间、录入比分与状态流转。 */

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { CalendarClock, Pencil, Plus, Trash2 } from "lucide-react";
import type { Schedule, TournamentDetail } from "../../../types";
import { ApiError, tournamentApi } from "../../../lib/api";
import {
  Badge,
  Button,
  Empty,
  Field,
  Input,
  Modal,
  Select,
  Spinner,
} from "../../../components/ui";
import { alertDialog, confirmDialog } from "../../../components/dialog";
import { formatDateTime } from "../../../lib/format";

const EMPTY_SCHEDULE = {
  phase_id: "",
  round: 1,
  round_name: "",
  bo: 1,
  is_final: false,
  home_team_id: "",
  away_team_id: "",
  start_time: "",
  status: 0,
  home_score: "",
  away_score: "",
};

export default function SchedulesTab({
  detail,
  onChanged,
}: {
  detail: TournamentDetail;
  onChanged: () => void;
}) {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Schedule | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    tournamentApi
      .schedules(detail.id)
      .then(setSchedules)
      .finally(() => setLoading(false));
  }, [detail.id]);

  useEffect(() => {
    load();
  }, [load]);

  const sections = useMemo(() => {
    const map = new Map<number, Schedule[]>();
    for (const s of schedules) {
      const key = s.phase_id ?? -1;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    }
    const result: { id: number; name: string; list: Schedule[] }[] = [];
    for (const p of detail.phases) {
      if (map.has(p.id)) result.push({ id: p.id, name: p.name, list: map.get(p.id)! });
    }
    if (map.has(-1)) result.push({ id: -1, name: "未分阶段", list: map.get(-1)! });
    return result;
  }, [schedules, detail.phases]);

  const remove = async (s: Schedule) => {
    if (!(await confirmDialog(`删除对局「${s.home_team_name} vs ${s.away_team_name}」？`, { title: "删除确认", danger: true }))) return;
    try {
      await tournamentApi.removeSchedule(s.id);
      load();
    } catch (err) {
      await alertDialog(err instanceof ApiError ? err.message : "删除失败", { title: "删除失败" });
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">对局列表</h2>
          <p className="mt-0.5 text-xs text-gray-400">共 {schedules.length} 场对局</p>
        </div>
        <Button size="sm" onClick={() => { setEditing(null); setModalOpen(true); }}>
          <Plus className="h-3.5 w-3.5" /> 新建对局
        </Button>
      </div>

      {loading ? (
        <Spinner text="加载对局…" />
      ) : schedules.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
          <Empty text="暂无对局，点击「新建对局」开始编排" />
        </div>
      ) : (
        <div className="space-y-5">
          {sections.map(({ id, name, list }) => (
            <section key={id} className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
              <h3 className="border-b border-gray-100 bg-gray-50 px-5 py-2.5 text-sm font-semibold text-gray-700">
                {name}
                <span className="ml-2 text-xs font-normal text-gray-400">{list.length} 场</span>
              </h3>
              <ul className="divide-y divide-gray-100">
                {list.map((s) => (
                    <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="text-sm text-gray-400">
                          {s.round_name || `第${s.round}轮`}
                          {s.is_final === 1 && <span className="ml-1 text-blue-600">决赛</span>}
                        </span>
                        <div className="flex items-center gap-2 text-sm font-medium">
                          <span className="truncate">{s.home_team_name}</span>
                          <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs">
                            {s.status === 2 ? `${s.home_score ?? 0} : ${s.away_score ?? 0}` : "vs"}
                          </span>
                          <span className="truncate">{s.away_team_name}</span>
                        </div>
                        <Badge label={s.status_label} status={s.status} kind="schedule" />
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                          <CalendarClock className="h-3.5 w-3.5" />
                          {formatDateTime(s.start_time)}
                          <span className="text-gray-300">|</span> BO{s.bo}
                        </span>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => { setEditing(s); setModalOpen(true); }}
                          >
                            <Pencil className="h-3.5 w-3.5" /> 管理
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => remove(s)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
            </section>
          ))}
        </div>
      )}

      <ScheduleModal
        detail={detail}
        open={modalOpen}
        schedule={editing}
        onClose={() => setModalOpen(false)}
        onSuccess={() => {
          setModalOpen(false);
          setEditing(null);
          load();
          onChanged();
        }}
      />
    </div>
  );
}

/** 新建 / 编辑对局弹窗 */
function ScheduleModal({
  detail,
  open,
  schedule,
  onClose,
  onSuccess,
}: {
  detail: TournamentDetail;
  open: boolean;
  schedule: Schedule | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEdit = schedule !== null;
  const [form, setForm] = useState(EMPTY_SCHEDULE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setError("");
    if (schedule) {
      setForm({
        phase_id: schedule.phase_id ? String(schedule.phase_id) : "",
        round: schedule.round,
        round_name: schedule.round_name ?? "",
        bo: schedule.bo,
        is_final: schedule.is_final === 1,
        home_team_id: schedule.home_team_id ? String(schedule.home_team_id) : "",
        away_team_id: schedule.away_team_id ? String(schedule.away_team_id) : "",
        start_time: toLocalInput(schedule.start_time),
        status: schedule.status,
        home_score: schedule.home_score === null ? "" : String(schedule.home_score),
        away_score: schedule.away_score === null ? "" : String(schedule.away_score),
      });
    } else {
      setForm({ ...EMPTY_SCHEDULE, phase_id: detail.phases[0] ? String(detail.phases[0].id) : "" });
    }
  }, [open, schedule, detail.phases]);

  const set = <K extends keyof typeof EMPTY_SCHEDULE>(key: K, value: (typeof EMPTY_SCHEDULE)[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const teamOptions = detail.teams.filter((t) => t.status !== 3);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.home_team_id || !form.away_team_id) {
      setError("请选择对阵双方队伍");
      return;
    }
    if (form.home_team_id === form.away_team_id) {
      setError("对阵双方不能是同一支队伍");
      return;
    }
    const body: Record<string, unknown> = {
      phase_id: form.phase_id ? Number(form.phase_id) : null,
      round: Number(form.round) || 1,
      round_name: form.round_name || null,
      bo: Number(form.bo) || 1,
      is_final: form.is_final,
      home_team_id: Number(form.home_team_id),
      away_team_id: Number(form.away_team_id),
      start_time: form.start_time || null,
    };
    if (isEdit) {
      body.status = Number(form.status);
      body.home_score = form.home_score === "" ? null : Number(form.home_score);
      body.away_score = form.away_score === "" ? null : Number(form.away_score);
    }
    setLoading(true);
    try {
      if (isEdit) await tournamentApi.updateSchedule(schedule.id, body);
      else await tournamentApi.createSchedule(detail.id, body);
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title={isEdit ? "管理对局" : "新建对局"}
      onClose={onClose}
      width="max-w-xl"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={submit} form="schedule-form" type="submit" loading={loading}>
            保存
          </Button>
        </>
      }
    >
      <form id="schedule-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="所属阶段">
          <Select value={form.phase_id} onChange={(e) => set("phase_id", e.target.value)}>
            <option value="">未分阶段</option>
            {detail.phases.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="轮次名称">
          <Input value={form.round_name} onChange={(e) => set("round_name", e.target.value)} placeholder="例如：第一轮 / 总决赛" maxLength={32} />
        </Field>
        <Field label="轮次序号">
          <Input type="number" min={1} value={form.round} onChange={(e) => set("round", Number(e.target.value))} />
        </Field>
        <Field label="赛制">
          <Select value={form.bo} onChange={(e) => set("bo", Number(e.target.value))}>
            <option value={1}>BO1</option>
            <option value={3}>BO3</option>
            <option value={5}>BO5</option>
          </Select>
        </Field>
        <Field label="主队（先手）">
          <Select value={form.home_team_id} onChange={(e) => set("home_team_id", e.target.value)}>
            <option value="">请选择队伍</option>
            {teamOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="客队（后手）">
          <Select value={form.away_team_id} onChange={(e) => set("away_team_id", e.target.value)}>
            <option value="">请选择队伍</option>
            {teamOptions.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="开赛时间">
          <Input type="datetime-local" value={form.start_time} onChange={(e) => set("start_time", e.target.value)} />
        </Field>
        <Field label="是否决赛">
          <Select
            value={form.is_final ? "1" : "0"}
            onChange={(e) => set("is_final", e.target.value === "1")}
          >
            <option value="0">否</option>
            <option value="1">是</option>
          </Select>
        </Field>
        {isEdit && (
          <>
            <Field label="对局状态">
              <Select value={String(form.status)} onChange={(e) => set("status", Number(e.target.value))}>
                <option value={0}>未开赛</option>
                <option value={1}>进行中</option>
                <option value={2}>已结束</option>
                <option value={3}>已取消</option>
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="主队比分">
                <Input type="number" min={0} value={form.home_score} onChange={(e) => set("home_score", e.target.value)} />
              </Field>
              <Field label="客队比分">
                <Input type="number" min={0} value={form.away_score} onChange={(e) => set("away_score", e.target.value)} />
              </Field>
            </div>
          </>
        )}
        {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}
        {!isEdit && (
          <p className="text-xs text-gray-400 sm:col-span-2">
            新建对局默认为「未开赛」，可在创建后设置开赛时间与录入比分。
          </p>
        )}
      </form>
    </Modal>
  );
}

function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
