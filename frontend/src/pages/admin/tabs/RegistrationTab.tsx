/** 报名管理：报名数据统计 + 队伍列表（确认/驳回/取消/添加队员/代报名建队/设队长）。 */

import { useState, type FormEvent } from "react";
import { Crown, Plus, Trash2, UserPlus, X } from "lucide-react";
import type { Team, TournamentDetail } from "../../../types";
import { ApiError, tournamentApi } from "../../../lib/api";
import {
  Badge,
  Button,
  Empty,
  Field,
  Input,
  Modal,
} from "../../../components/ui";
import { formatDateTime, playerStatusLabel } from "../../../lib/format";

export default function RegistrationTab({
  detail,
  onChanged,
}: {
  detail: TournamentDetail;
  onChanged: () => void;
}) {
  const stats = detail.stats;
  const [addTeamOpen, setAddTeamOpen] = useState(false);
  const [addingPlayerTeamId, setAddingPlayerTeamId] = useState<number | null>(null);

  const cards = [
    { label: "报名队伍", value: stats.team_count, cls: "text-gray-900" },
    { label: "待审核队伍", value: stats.pending_team_count, cls: "text-amber-600" },
    { label: "已确认队伍", value: stats.confirmed_team_count, cls: "text-emerald-600" },
    { label: "报名总人数", value: stats.player_count, cls: "text-blue-600" },
  ];

  const teamAction = async (team: Team, status: number, tip: string) => {
    if (!window.confirm(`确定${tip}「${team.name}」吗？`)) return;
    try {
      await tournamentApi.teamStatus(team.id, status);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  const removeTeam = async (team: Team) => {
    if (!window.confirm(`删除队伍「${team.name}」及其所有队员？`)) return;
    try {
      await tournamentApi.removeTeam(team.id);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "删除失败");
    }
  };

  const playerAction = async (playerId: number, status: string) => {
    try {
      await tournamentApi.playerStatus(playerId, status);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  const removePlayer = async (playerId: number) => {
    try {
      await tournamentApi.removePlayer(playerId);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "删除失败");
    }
  };

  const setCaptain = async (playerId: number, nickname: string) => {
    if (!window.confirm(`将「${nickname}」设为队长？原队长将转为普通队员。`)) return;
    try {
      await tournamentApi.setCaptain(playerId);
      onChanged();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "操作失败");
    }
  };

  return (
    <div className="space-y-5">
      {/* 统计 */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-gray-400">{c.label}</p>
            <p className={`mt-1 text-2xl font-semibold ${c.cls}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold">报名队伍</h2>
          <Button size="sm" onClick={() => setAddTeamOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> 代报名建队
          </Button>
        </div>
        {detail.teams.length === 0 ? (
          <Empty text="暂无队伍报名" />
        ) : (
          <ul className="divide-y divide-gray-100">
            {detail.teams.map((team) => (
              <li key={team.id} className="px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{team.name}</span>
                    <Badge label={team.status_label} status={team.status} kind="team" />
                    <span className="text-xs text-gray-400">
                      {team.player_count} 人 · {formatDateTime(team.created_at)} 报名
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {team.status === 0 && (
                      <>
                        <Button size="sm" variant="success" onClick={() => teamAction(team, 1, "确认报名")}>
                          确认
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => teamAction(team, 2, "驳回报名")}>
                          驳回
                        </Button>
                      </>
                    )}
                    {team.status !== 3 && (
                      <Button size="sm" variant="secondary" onClick={() => setAddingPlayerTeamId(team.id)}>
                        <UserPlus className="h-3.5 w-3.5" /> 添加队员
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => removeTeam(team)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
                {/* 队员列表 */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {team.players.map((p) => (
                    <span
                      key={p.id}
                      className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 py-1 pl-3 pr-1 text-xs"
                    >
                      {p.is_captain === 1 && (
                        <span className="inline-flex items-center gap-0.5 text-amber-600">
                          <Crown className="h-3 w-3" /> 队长
                        </span>
                      )}
                      {p.nickname}
                      <span className="text-gray-400">{playerStatusLabel(p.status)}</span>
                      {p.status === "PENDING" && (
                        <>
                          <button
                            className="rounded-full bg-emerald-100 px-1.5 text-emerald-600 hover:bg-emerald-200"
                            onClick={() => playerAction(p.id, "AGREED")}
                          >
                            同意
                          </button>
                          <button
                            className="rounded-full bg-red-100 px-1.5 text-red-600 hover:bg-red-200"
                            onClick={() => playerAction(p.id, "REJECTED")}
                          >
                            拒绝
                          </button>
                        </>
                      )}
                      {p.is_captain !== 1 && (
                        <button
                          className="rounded-full bg-blue-50 px-1.5 text-blue-600 hover:bg-blue-100"
                          onClick={() => setCaptain(p.id, p.nickname)}
                          title="把该队员设为队长"
                        >
                          设为队长
                        </button>
                      )}
                      <button
                        className="rounded-full p-0.5 text-gray-400 hover:bg-gray-200"
                        onClick={() => removePlayer(p.id)}
                        title="移除队员"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <AddTeamModal
        detail={detail}
        open={addTeamOpen}
        onClose={() => setAddTeamOpen(false)}
        onSuccess={() => {
          setAddTeamOpen(false);
          onChanged();
        }}
      />
      <AddPlayerModal
        teamId={addingPlayerTeamId}
        open={addingPlayerTeamId !== null}
        onClose={() => setAddingPlayerTeamId(null)}
        onSuccess={() => {
          setAddingPlayerTeamId(null);
          onChanged();
        }}
      />
    </div>
  );
}

/** 办赛者代报名建队 */
function AddTeamModal({
  detail,
  open,
  onClose,
  onSuccess,
}: {
  detail: TournamentDetail;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isSolo = detail.team_mode === 2;
  const [name, setName] = useState("");
  const [rows, setRows] = useState<{ nickname: string; captain: boolean }[]>([
    { nickname: "", captain: true },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const players = rows
      .filter((r) => r.nickname.trim())
      .map((r) => ({ nickname: r.nickname.trim(), is_captain: r.captain }));
    if (isSolo) {
      if (!players.length) {
        setError("请填写参赛选手昵称");
        return;
      }
    } else if (!name.trim()) {
      setError("请填写队伍名");
      return;
    }
    setLoading(true);
    try {
      await tournamentApi.createTeamByOrganizer(detail.id, {
        name: name.trim() || players[0]?.nickname || name.trim(),
        players,
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title="代报名建队"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={submit} form="add-team-form" type="submit" loading={loading}>
            创建队伍
          </Button>
        </>
      }
    >
      <form id="add-team-form" onSubmit={submit} className="space-y-3">
        {!isSolo && (
          <Field label="队伍名" required>
            <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={64} />
          </Field>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            队员（{isSolo ? "选手" : `最多 ${detail.max_team_members} 人，可不填`}）
          </label>
          <div className="space-y-2">
            {rows.map((r, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  value={r.nickname}
                  onChange={(e) =>
                    setRows((prev) => prev.map((v, j) => (j === i ? { ...v, nickname: e.target.value } : v)))
                  }
                  placeholder={`队员 ${i + 1} 昵称`}
                  maxLength={64}
                />
                <label className="flex shrink-0 items-center gap-1 whitespace-nowrap text-xs text-gray-500">
                  <input
                    type="checkbox"
                    checked={r.captain}
                    onChange={(e) =>
                      setRows((prev) => prev.map((v, j) => (j === i ? { ...v, captain: e.target.checked } : v)))
                    }
                  />
                  队长
                </label>
                {rows.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setRows((prev) => prev.filter((_, j) => j !== i))}
                  >
                    <X className="h-4 w-4 text-red-500" />
                  </Button>
                )}
              </div>
            ))}
          </div>
          {!isSolo && rows.length < detail.max_team_members && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="mt-2"
              onClick={() => setRows((prev) => [...prev, { nickname: "", captain: false }])}
            >
              <Plus className="h-3.5 w-3.5" /> 添加队员
            </Button>
          )}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-xs text-gray-400">代报名队伍默认直接确认，无需再审核；不填队员可先建队，稍后再补。</p>
      </form>
    </Modal>
  );
}

/** 给已有队伍添加队员 */
function AddPlayerModal({
  teamId,
  open,
  onClose,
  onSuccess,
}: {
  teamId: number | null;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [nickname, setNickname] = useState("");
  const [asCaptain, setAsCaptain] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!nickname.trim() || teamId === null) return;
    setLoading(true);
    try {
      await tournamentApi.addPlayer(teamId, nickname.trim(), asCaptain);
      setNickname("");
      setAsCaptain(false);
      onSuccess();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "添加失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      title="添加队员"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={submit} form="add-player-form" type="submit" loading={loading}>
            添加
          </Button>
        </>
      }
    >
      <form id="add-player-form" onSubmit={submit} className="space-y-3">
        <Field label="队员昵称" required>
          <Input
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="输入昵称"
            maxLength={64}
            autoFocus
          />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={asCaptain}
            onChange={(e) => setAsCaptain(e.target.checked)}
          />
          设为队长（原队长自动转为普通队员）
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
    </Modal>
  );
}
