/** 官网：自然语言问数助手（不强制登录：游客仅公开数据；预制提示词按登录态+角色展示）。
 * 支持多个对话窗口：左侧会话列表可新建/切换/删除，每个窗口独立消息历史。
 *
 * 本次增强：
 * 1) 聊天式布局：消息区占满视口并滚动，输入框固定到底部；
 * 2) 对话数据持久化到 IndexedDB：切换 tab / 刷新后恢复（按用户隔离，游客=guest）；
 * 3) MCP 接入已独立为「MCP 服务」页面（/mcp），与问数助手在导航栏并列。 */

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  Plus,
  Send,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import { fetchPresets, streamQuery } from "../../lib/agentApi";
import type { AgentEvent, DoneEvent, PresetQuery } from "../../types";
import { useAuth } from "../../lib/auth";
import { ROLE_LABELS } from "../../types";
import { api } from "../../lib/api";
import { Button, Modal } from "../../components/ui";
import { confirmDialog } from "../../components/dialog";
import { idbGet, idbSet } from "../../lib/idb";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  events: AgentEvent[];
  error?: string;
}

/** 一个对话窗口：独立消息历史，标题取首条提问 */
interface Conversation {
  id: number;
  title: string;
  messages: Message[];
}

/** IndexedDB 中保存的会话快照 */
interface ConversationSnapshot {
  conversations: Conversation[];
  activeId: number;
  seq: number;
}

type NodeStatus = "pending" | "running" | "success" | "error" | "warning";

interface FanoutNode {
  step: string;
  label: string;
  hint?: string;
  branch?: "error"; // 仅异常时触发的条件边
}
interface PipelineGroup {
  step: string;
  label: string;
  fanout?: FanoutNode[];
}

// 与 app/agent/graph.py 的 DAG 拓扑一致：
// 抽取关键词 → 三路并行召回(字段/取值/指标) → 合并 → 两路并行过滤(表/指标)
//   → 补充上下文 → 生成 SQL → 校验 SQL →(成功)执行 /(语法错)修正后执行 /(权限)直接结束
const PIPELINE: PipelineGroup[] = [
  {
    step: "抽取关键词",
    label: "提取关键词",
    fanout: [
      { step: "召回字段信息", label: "召回字段" },
      { step: "召回字段取值", label: "召回字段取值" },
      { step: "召回指标信息", label: "召回指标" },
    ],
  },
  {
    step: "合并召回信息",
    label: "合并召回",
    fanout: [
      { step: "过滤表信息", label: "过滤候选表" },
      { step: "过滤指标信息", label: "过滤指标" },
    ],
  },
  { step: "添加额外上下文", label: "补充上下文" },
  { step: "生成SQL", label: "生成 SQL" },
  {
    step: "校验SQL",
    label: "校验 SQL",
    fanout: [{ step: "校正SQL", label: "修正 SQL", branch: "error", hint: "语法错时" }],
  },
  { step: "执行SQL", label: "执行查询" },
];

// 逐事件收敛每个节点状态：终态（成功/失败）一旦达成即锁定，不被后续 running 覆盖
function buildStatusMap(events: AgentEvent[]): Record<string, NodeStatus> {
  const map: Record<string, NodeStatus> = {};
  for (const e of events) {
    if (e.type !== "progress") continue;
    const prev = map[e.step];
    if (prev === "success" || prev === "error") continue;
    map[e.step] = e.status as NodeStatus;
  }
  return map;
}

function StatusIcon({ status }: { status: NodeStatus }) {
  switch (status) {
    case "running":
      return <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-blue-500" />;
    case "success":
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-500" />;
    case "error":
      return <XCircle className="h-3.5 w-3.5 shrink-0 text-red-500" />;
    case "warning":
      return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-500" />;
    default:
      return <Circle className="h-3.5 w-3.5 shrink-0 text-gray-300" />;
  }
}

function NodeRow({
  status,
  label,
  hint,
  muted,
}: {
  status: NodeStatus;
  label: string;
  hint?: string;
  muted?: boolean;
}) {
  const dim = muted || status === "pending";
  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      <StatusIcon status={status} />
      <span className={dim ? "text-gray-400" : "text-gray-700"}>{label}</span>
      {hint && <span className="rounded bg-gray-100 px-1 text-[10px] text-gray-400">{hint}</span>}
      {status === "running" && <span className="text-blue-400">运行中…</span>}
    </div>
  );
}

/** 问数执行过程：按真实 DAG 渲染成树形，每个节点独立显示 等待/运行中/成功/失败 状态 */
function NodeGraph({ events }: { events: AgentEvent[] }) {
  const status = buildStatusMap(events);
  const done = events.find((e) => e.type === "done") as DoneEvent | undefined;
  return (
    <div className="space-y-1.5 text-sm">
      {PIPELINE.map((group, gi) => {
        const gStatus = status[group.step] ?? "pending";
        const children = group.fanout ?? [];
        return (
          <div key={group.step}>
            {gi > 0 && <div className="ml-[7px] h-2 w-px bg-gray-200" />}
            <NodeRow status={gStatus} label={group.label} />
            {children.length > 0 && (
              <div className="ml-[7px] border-l border-gray-200 pl-3">
                {children.map((c) => {
                  const cStatus = status[c.step] ?? "pending";
                  const activated = cStatus !== "pending";
                  return (
                    <div key={c.step} className="relative mt-1.5">
                      <span className="absolute -left-3 top-[7px] h-px w-3 bg-gray-200" />
                      <NodeRow
                        status={cStatus}
                        label={c.label}
                        hint={c.hint}
                        muted={c.branch === "error" && !activated}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      {done?.sql && (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-50 p-2 text-xs text-gray-700">
          {done.sql}
        </pre>
      )}
      {done?.error && <div className="mt-1 text-xs text-red-500">错误：{done.error}</div>}
    </div>
  );
}

// 当前可查询范围的说明（docs/permission-design.md 第 3 节）
const SCOPE_HINTS: Record<string, string> = {
  guest: "游客模式：仅可查询已发布的公开赛事信息（赛程/比分/报名统计），无法查询选手与用户明细",
  player: "玩家模式：可查询已发布赛事公开信息，以及自己的队伍与报名信息",
  organizer: "办赛者模式：可查询自己创办的赛事全部数据 + 平台已发布赛事公开信息",
  operator: "运营模式：可查询平台全部数据（敏感字段仅限本人）",
  super_admin: "超级管理员：可查询平台全部数据",
};

function ResultTable({ done }: { done: DoneEvent }) {
  const columns = done.result?.columns ?? [];
  const rows = done.result?.rows ?? [];
  if (!columns.length) return <div className="text-sm text-gray-400">（无结果）</div>;
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} className="border-b px-3 py-1.5 text-left font-medium text-gray-600">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="odd:bg-gray-50">
              {columns.map((c) => (
                <td key={c} className="border-b px-3 py-1.5 text-gray-700">
                  {String(row[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** 预制提示词 chips：点击直接提问；带 params 的（需选赛事）先弹赛事选择器 */
function PresetChips({
  presets,
  onPick,
}: {
  presets: PresetQuery[];
  onPick: (template: string, presets: PresetQuery[]) => void;
}) {
  if (!presets.length) return null;
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {presets.map((p) => (
        <button
          key={p.id}
          onClick={() => onPick(p.template, [p])}
          className="inline-flex items-center gap-1 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-sm text-blue-700 transition-colors hover:border-blue-300 hover:bg-blue-100"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {p.title}
        </button>
      ))}
    </div>
  );
}

export default function AskPage() {
  const { user } = useAuth();
  // 多窗口对话：会话列表 + 当前活跃窗口，各自独立消息历史
  const seqRef = useRef(1);
  const [conversations, setConversations] = useState<Conversation[]>([
    { id: 1, title: "新对话", messages: [] },
  ]);
  const [activeId, setActiveId] = useState(1);
  const [hydrated, setHydrated] = useState(false);
  const active = conversations.find((c) => c.id === activeId) ?? conversations[0];

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [presets, setPresets] = useState<PresetQuery[]>([]);
  const [presetModal, setPresetModal] = useState<PresetQuery | null>(null);
  const [tournaments, setTournaments] = useState<{ id: number; name: string }[]>([]);
  const [tournamentLoading, setTournamentLoading] = useState(false);
  const [selectedTournamentId, setSelectedTournamentId] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 会话按用户隔离：未登录 = guest；登录后按 user.id 分区
  const storageKey = `ask-${user?.id ?? "guest"}`;

  // 进入页面 / 切换账号时从 IndexedDB 恢复会话
  useEffect(() => {
    let alive = true;
    setHydrated(false);
    (async () => {
      const saved = await idbGet<ConversationSnapshot>(storageKey);
      if (!alive) return;
      if (saved && saved.conversations.length > 0) {
        seqRef.current = saved.seq || 1;
        setConversations(saved.conversations);
        setActiveId(saved.activeId ?? saved.conversations[0].id);
      } else {
        seqRef.current = 1;
        setConversations([{ id: 1, title: "新对话", messages: [] }]);
        setActiveId(1);
      }
      setHydrated(true);
    })();
    return () => {
      alive = false;
    };
  }, [storageKey]);

  // 会话变化（防抖 300ms）写入 IndexedDB，切换 tab / 刷新后数据保留
  useEffect(() => {
    if (!hydrated) return;
    const timer = setTimeout(() => {
      void idbSet<ConversationSnapshot>(storageKey, {
        conversations,
        activeId,
        seq: seqRef.current,
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [conversations, activeId, hydrated, storageKey]);

  // 预制提示词按登录态 + 角色加载（游客只拿到公开 4 条）
  useEffect(() => {
    fetchPresets().then(setPresets).catch(() => setPresets([]));
  }, [user?.id]);

  const send = async (queryText?: string) => {
    const query = (queryText ?? input).trim();
    if (!query || loading) return;
    setInput("");
    const id = ++seqRef.current;
    // 首条提问作为会话标题（截断），消息追加到活跃窗口
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? {
              ...c,
              title: c.messages.length === 0 ? query.slice(0, 24) : c.title,
              messages: [
                ...c.messages,
                { id, role: "user", content: query, events: [] },
                { id: id + 0.5, role: "assistant", content: "", events: [] },
              ],
            }
          : c,
      ),
    );
    setLoading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamQuery(
        query,
        (event) => {
          setConversations((prev) =>
            prev.map((c) =>
              c.id === activeId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === id + 0.5 ? { ...m, events: [...m.events, event] } : m,
                    ),
                  }
                : c,
            ),
          );
        },
        controller.signal,
      );
    } catch (err) {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === id + 0.5
                    ? { ...m, error: err instanceof Error ? err.message : String(err) }
                    : m,
                ),
              }
            : c,
        ),
      );
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.nativeEvent.isComposing) send();
  };

  const doneEvent = (m: Message): DoneEvent | undefined =>
    m.events.find((e) => e.type === "done") as DoneEvent | undefined;

  // 新建对话窗口并切换过去
  const newConversation = () => {
    const fresh = { id: ++seqRef.current, title: "新对话", messages: [] };
    setConversations((prev) => [...prev, fresh]);
    setActiveId(fresh.id);
  };

  // 删除对话窗口（保留最后一个时自动新建一个空窗口）
  const removeConversation = async (id: number) => {
    if (!(await confirmDialog("删除该对话窗口？其中的对话记录将不可恢复。"))) return;
    const next = conversations.filter((c) => c.id !== id);
    if (next.length === 0) {
      const fresh = { id: ++seqRef.current, title: "新对话", messages: [] };
      setConversations([fresh]);
      setActiveId(fresh.id);
    } else {
      setConversations(next);
      if (id === activeId) setActiveId(next[next.length - 1].id);
    }
  };

  // 点击预制提示词：无参数直接提问；有参数（需选赛事）弹选择器
  const onPickPreset = (template: string, picked: PresetQuery[]) => {
    const p = picked[0];
    if (p && p.params.length > 0) {
      setPresetModal(p);
      if (tournaments.length === 0) {
        setTournamentLoading(true);
        api<{ id: number; name: string }[]>("/api/tournaments?scope=published")
          .then((list) => {
            setTournaments(list);
            setSelectedTournamentId(list[0]?.id ?? null);
          })
          .catch(() => setTournaments([]))
          .finally(() => setTournamentLoading(false));
      } else {
        setSelectedTournamentId(tournaments[0].id);
      }
      return;
    }
    send(template);
  };

  const submitPreset = () => {
    if (!presetModal) return;
    const selected =
      tournaments.find((t) => t.id === selectedTournamentId) ?? tournaments[0];
    if (!selected) return;
    const query = presetModal.template.replaceAll("{{赛事名}}", selected.name);
    setPresetModal(null);
    send(query);
  };

  const scopeHint = SCOPE_HINTS[user?.role ?? "guest"] ?? SCOPE_HINTS.guest;
  const messages = active.messages;

  return (
    <div className="mx-auto flex h-[calc(100vh-6.5rem)] min-h-[520px] max-w-5xl flex-col gap-4 md:flex-row">
      {/* 会话列表：新建/切换/删除窗口（窄屏横向滚动，宽屏纵向） */}
      <aside className="flex w-full shrink-0 flex-col gap-1 md:w-56">
        <button
          onClick={newConversation}
          className="flex items-center justify-center gap-1.5 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
        >
          <Plus className="h-4 w-4" /> 新对话
        </button>
        <div className="flex min-h-0 flex-1 gap-1 overflow-x-auto pb-1 md:flex-col md:overflow-x-visible md:overflow-y-auto">
          {conversations.map((c) => {
            const isActive = c.id === activeId;
            return (
              <div
                key={c.id}
                className={`group flex shrink-0 items-center gap-1 rounded-xl border px-3 py-2 ${
                  isActive
                    ? "border-blue-200 bg-blue-50"
                    : "border-gray-200 bg-white hover:bg-gray-50"
                }`}
              >
                <button
                  onClick={() => setActiveId(c.id)}
                  className="min-w-0 flex-1 truncate text-left text-sm text-gray-700"
                  title={c.title}
                >
                  {c.title}
                </button>
                {conversations.length > 1 && (
                  <button
                    onClick={() => removeConversation(c.id)}
                    className="shrink-0 rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-red-500 md:opacity-0 md:group-hover:opacity-100"
                    title="删除对话窗口"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* 当前窗口对话区：消息区滚动，输入框固定底部 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="mb-4 shrink-0 text-center">
          <h1 className="text-2xl font-semibold text-gray-900">赛事问数助手</h1>
          <p className="mt-1 text-sm text-gray-500">用自然语言查询赛程、比分、报名与统计</p>
          <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 text-xs text-amber-700">
            {user ? `已登录 · ${ROLE_LABELS[user.role ?? "player"] ?? "玩家"}` : "游客模式（未登录）"} · {scopeHint}
          </p>
        </header>
        <main className="min-h-0 flex-1 space-y-4 overflow-y-auto pb-4">
          {!hydrated ? (
            <div className="flex h-full items-center justify-center text-sm text-gray-400">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> 正在恢复对话…
            </div>
          ) : (
            <>
              {messages.length === 0 && (
                <div className="space-y-4 pt-8 text-center">
                  <p className="text-sm text-gray-400">
                    试试问：「XX 队最近 5 场比赛的比分」或「本届赛事小组赛积分榜」
                  </p>
                  <PresetChips presets={presets} onPick={onPickPreset} />
                </div>
              )}
              {messages.map((m) =>
                m.role === "user" ? (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2 text-white shadow-sm">
                      {m.content}
                    </div>
                  </div>
                ) : (
                  <div key={m.id} className="flex justify-start">
                    <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-gray-200 bg-white p-4 shadow-sm">
                      {m.events.length === 0 && !m.error && (
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <Loader2 className="h-4 w-4 animate-spin" /> 思考中…
                        </div>
                      )}
                      {m.events.length > 0 && (
                        <>
                          <NodeGraph events={m.events} />
                          {doneEvent(m) && <ResultTable done={doneEvent(m)!} />}
                        </>
                      )}
                      {m.error && <div className="text-sm text-red-500">{m.error}</div>}
                    </div>
                  </div>
                ),
              )}
            </>
          )}
        </main>
        <footer className="shrink-0 bg-gradient-to-t from-gray-50 via-gray-50 to-transparent px-1 pb-1 pt-6">
          <div className="flex items-center gap-2 rounded-2xl border border-gray-200 bg-white p-2 pl-4 shadow-lg shadow-gray-200/60">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="输入赛事问题…"
              className="flex-1 bg-transparent text-sm text-gray-800 outline-none placeholder:text-gray-400"
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
              title="发送"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-gray-400">问数助手基于赛事库自动查询，结果仅供参考</p>
        </footer>
      </div>

      {/* 带参数的预制提示词：选择赛事后生成问题 */}
      <Modal
        open={presetModal !== null}
        title={presetModal?.title ?? "选择赛事"}
        onClose={() => setPresetModal(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPresetModal(null)}>
              取消
            </Button>
            <Button onClick={submitPreset} disabled={tournaments.length === 0 || tournamentLoading}>
              生成问题
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-500">选择要分析的赛事：</p>
          {tournamentLoading ? (
            <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" /> 加载赛事列表…
            </div>
          ) : tournaments.length === 0 ? (
            <div className="py-4 text-sm text-gray-400">暂无可选赛事</div>
          ) : (
            <div className="max-h-64 space-y-1 overflow-y-auto">
              {tournaments.map((t) => (
                <label
                  key={t.id}
                  className="flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm hover:bg-blue-50"
                >
                  <input
                    type="radio"
                    name="preset-tournament"
                    checked={t.id === selectedTournamentId}
                    onChange={() => setSelectedTournamentId(t.id)}
                  />
                  <span className="text-gray-800">{t.name}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
