/** 极简 MCP（Model Context Protocol）streamable-http 客户端。
 *
 * 用途：Ask 页「MCP 接入」开关启用后，连接指定 MCP 服务（如项目自带
 * app/mcp/server.py 的 streamable-http 模式），完成 initialize 握手并拉取
 * tools/list 工具清单，用于验证连通性与展示可用工具。
 *
 * 不依赖 @modelcontextprotocol/sdk，直接用 fetch 完成 JSON-RPC 交互；
 * 支持无状态模式（无 mcp-session-id）与有状态模式（带上响应头返回的 session）。
 */

export interface MCPToolInfo {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

export interface MCPConnectResult {
  ok: boolean;
  serverName?: string;
  protocolVersion?: string;
  tools: MCPToolInfo[];
  error?: string;
}

const PROTOCOL_VERSION = "2025-03-26";

interface RpcResponse {
  result?: unknown;
  error?: { message?: string; code?: number };
}

/** 解析 MCP streamable-http 响应：可能是纯 JSON，也可能是 SSE（event: message + data: {...}）。 */
function parseMCPResponse(text: string): RpcResponse {
  try {
    return JSON.parse(text) as RpcResponse;
  } catch {
    // SSE 解析：按空行切分消息块，收集每块的 data: 行（多行 data 拼接）
    const parsed: RpcResponse[] = [];
    for (const block of text.split(/\n\n+/)) {
      let data = "";
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith("data:")) data += line.slice(5).trimStart() + "\n";
      }
      data = data.trim();
      if (data) {
        try {
          parsed.push(JSON.parse(data) as RpcResponse);
        } catch {
          // 忽略无法解析的 data 行
        }
      }
    }
    // 优先取包含 result 的消息（MCP 单请求单响应）
    const withResult = parsed.find((m) => m && "result" in m && m.result !== undefined);
    if (withResult) return withResult;
    const first = parsed[0];
    if (first) return first;
    throw new Error("MCP 响应格式无法解析");
  }
}

async function mcpRequest(
  url: string,
  method: string,
  params: unknown,
  sessionId: string | null,
): Promise<{ result: unknown; sessionId: string | null }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  const nextSession = resp.headers.get("mcp-session-id") ?? sessionId;
  if (!resp.ok) {
    const body = (await resp.text()).slice(0, 200);
    throw new Error(`HTTP ${resp.status}${body ? `：${body}` : ""}`);
  }
  const json = parseMCPResponse(await resp.text());
  if (json.error) {
    throw new Error(json.error.message ?? `MCP 错误 ${json.error.code ?? ""}`.trim());
  }
  return { result: json.result, sessionId: nextSession };
}

/** 连接指定 streamable-http MCP 服务：initialize → notifications/initialized → tools/list */
export async function connectMCP(url: string): Promise<MCPConnectResult> {
  try {
    let session: string | null = null;

    const init = await mcpRequest(
      url,
      "initialize",
      {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {},
        clientInfo: { name: "tournament-agent-web", version: "0.1.0" },
      },
      null,
    );
    session = init.sessionId;

    // notifications/initialized（无需响应，失败忽略；无状态服务器也可正常继续）
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
        ...(session ? { "mcp-session-id": session } : {}),
      },
      body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized", params: {} }),
    }).catch(() => {});

    const list = await mcpRequest(url, "tools/list", {}, session);
    const tools = ((list.result as { tools?: MCPToolInfo[] } | undefined)?.tools ?? []) as MCPToolInfo[];
    const initResult = init.result as { serverInfo?: { name?: string } } | undefined;
    const serverName = initResult?.serverInfo?.name;

    return { ok: true, serverName, protocolVersion: PROTOCOL_VERSION, tools };
  } catch (e) {
    return {
      ok: false,
      tools: [],
      error: e instanceof Error ? e.message : String(e),
    };
  }
}
