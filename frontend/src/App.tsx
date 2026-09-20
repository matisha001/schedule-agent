import { useRef, useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import { streamQuery } from './lib/agentApi'
import type { AgentEvent, DoneEvent } from './types'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  events: AgentEvent[]
  error?: string
}

const STEP_LABELS: Record<string, string> = {
  extract_keywords: '提取关键词',
  recall: '召回知识',
  generate_sql: '生成 SQL',
  validate_sql: '校验 SQL',
  run_sql: '执行查询',
  correct_sql: '修正 SQL',
}

let msgSeq = 0

function StepTimeline({ events }: { events: AgentEvent[] }) {
  const steps = events.filter((e) => e.type === 'progress')
  const done = events.find((e) => e.type === 'done') as DoneEvent | undefined

  return (
    <div className="space-y-1.5 text-sm">
      {steps.map((e, i) => {
        const label = STEP_LABELS[e.step] ?? e.step
        const icon =
          e.status === 'success' ? '✅' : e.status === 'error' ? '❌' : e.status === 'warning' ? '⚠️' : '🔄'
        return (
          <div key={i} className="flex items-center gap-2 font-mono text-xs">
            <span>{icon}</span>
            <span className="text-gray-600 dark:text-gray-400">{label}</span>
            {e.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
            {e.status !== 'running' && e.message && (
              <span className="truncate text-gray-400">{e.message}</span>
            )}
          </div>
        )
      })}
      {done?.sql && (
        <pre className="mt-2 overflow-x-auto rounded bg-gray-100 p-2 text-xs dark:bg-gray-800">
          {done.sql}
        </pre>
      )}
      {done?.error && <div className="mt-1 text-xs text-red-500">错误：{done.error}</div>}
    </div>
  )
}

function ResultTable({ done }: { done: DoneEvent }) {
  const columns = done.result?.columns ?? []
  const rows = done.result?.rows ?? []
  if (!columns.length) {
    return <div className="text-sm text-gray-400">（无结果）</div>
  }
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c} className="border-b px-3 py-1.5 text-left font-medium text-gray-600 dark:text-gray-300">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="odd:bg-gray-50 dark:odd:bg-gray-800/50">
              {columns.map((c) => (
                <td key={c} className="border-b px-3 py-1.5 text-gray-700 dark:text-gray-200">
                  {String(row[c] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const send = async () => {
    const query = input.trim()
    if (!query || loading) return
    setInput('')
    const id = ++msgSeq
    setMessages((prev) => [
      ...prev,
      { id, role: 'user', content: query, events: [] },
      { id: id + 0.5, role: 'assistant', content: '', events: [] },
    ])
    setLoading(true)
    const controller = new AbortController()
    abortRef.current = controller
    try {
      await streamQuery(
        query,
        (event) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === id + 0.5 ? { ...m, events: [...m.events, event] } : m,
            ),
          )
        },
        controller.signal,
      )
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id + 0.5
            ? { ...m, error: err instanceof Error ? err.message : String(err) }
            : m,
        ),
      )
    } finally {
      setLoading(false)
    }
  }

  const doneEvent = (m: Message): DoneEvent | undefined =>
    m.events.find((e) => e.type === 'done') as DoneEvent | undefined

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col p-4">
      <header className="mb-4 text-center">
        <h1 className="text-2xl font-semibold">赛事管理 Agent</h1>
        <p className="text-sm text-gray-500">用自然语言查询赛程、比分、积分与统计</p>
      </header>

      <main className="flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && (
          <div className="pt-16 text-center text-sm text-gray-400">
            试试问：「XX 队最近 5 场比赛的比分」或「本届赛事小组赛积分榜」
          </div>
        )}
        {messages.map((m) =>
          m.role === 'user' ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl bg-blue-600 px-4 py-2 text-white">{m.content}</div>
            </div>
          ) : (
            <div key={m.id} className="flex justify-start">
              <div className="max-w-[90%] rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
                {m.events.length === 0 && !m.error && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Loader2 className="h-4 w-4 animate-spin" /> 思考中…
                  </div>
                )}
                {m.events.length > 0 && (
                  <>
                    <StepTimeline events={m.events} />
                    {doneEvent(m) && <ResultTable done={doneEvent(m)!} />}
                  </>
                )}
                {m.error && <div className="text-sm text-red-500">{m.error}</div>}
              </div>
            </div>
          ),
        )}
      </main>

      <footer className="sticky bottom-0 border-t border-gray-200 bg-white/90 py-3 backdrop-blur dark:border-gray-800 dark:bg-gray-950/90">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="输入赛事问题…"
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-900"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="rounded-xl bg-blue-600 p-2.5 text-white disabled:opacity-40"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </footer>
    </div>
  )
}
