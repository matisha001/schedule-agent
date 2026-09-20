/** SSE 流式问数请求（参照 k.md 四：fetch ReadableStream 手动解析） */

import type { AgentEvent } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function streamQuery(
  query: string,
  onEvent: (event: AgentEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ query }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`请求失败：HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split(/\n\n/);
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const payload = chunk
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.replace(/^data:\s?/, ""))
        .join("\n")
        .trim();
      if (payload) {
        try {
          onEvent(JSON.parse(payload) as AgentEvent);
        } catch {
          // 跳过无法解析的事件帧
        }
      }
    }
  }
}
