/** SSE 事件类型定义 */

export interface ProgressEvent {
  type: "progress";
  step: string;
  status: "running" | "success" | "error" | "warning";
  message?: string;
  keywords?: string[];
  hits?: { columns: number; metrics: number; values: number };
  rows?: number;
  sql?: string;
  error?: string;
}

export interface DoneEvent {
  type: "done";
  result?: { columns: string[]; rows: Record<string, unknown>[] } | null;
  sql?: string;
  error?: string;
}

export type AgentEvent = ProgressEvent | DoneEvent;
