/** 官网：MCP 服务接入配置页（与「问数助手」在导航栏并列）。
 * 页面上配置 streamable-http 服务地址 + 启用开关，连接后展示可用工具清单。
 * 配置持久化到 localStorage（全局生效），连接结果仅存于本页内存。 */

import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, Plug, XCircle } from "lucide-react";
import { connectMCP, type MCPConnectResult, type MCPToolInfo } from "../../lib/mcpClient";
import { Button } from "../../components/ui";

interface McpConfig {
  enabled: boolean;
  url: string;
}

// MCP Python SDK 的 streamable-http 端点挂载在 /mcp（POST 根路径会 404）
const DEFAULT_MCP_URL = "http://127.0.0.1:8899/mcp";
const MCP_CONFIG_KEY = "ask-mcp-config";

export default function McpPage() {
  const [config, setConfig] = useState<McpConfig>({ enabled: false, url: DEFAULT_MCP_URL });
  const [connecting, setConnecting] = useState(false);
  const [result, setResult] = useState<MCPConnectResult | null>(null);
  // 开关被「打开」后触发一次自动连接（含从本地配置恢复为开启的情况）
  const justEnabled = useRef(false);

  // 初始读取本地配置
  useEffect(() => {
    try {
      const raw = localStorage.getItem(MCP_CONFIG_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<McpConfig>;
        const savedUrl =
          typeof parsed.url === "string" && parsed.url.trim() ? parsed.url.trim() : "";
        // 迁移：旧版默认地址不带 /mcp 端点路径（POST 根路径会 404），自动补全
        const migratedUrl = savedUrl === "http://127.0.0.1:8899" ? DEFAULT_MCP_URL : savedUrl;
        setConfig((prev) => ({
          enabled: typeof parsed.enabled === "boolean" ? parsed.enabled : prev.enabled,
          url: migratedUrl || prev.url,
        }));
        if (parsed.enabled === true) justEnabled.current = true;
      }
    } catch {
      // 配置损坏时忽略，使用默认值
    }
  }, []);

  // 配置变化即持久化
  useEffect(() => {
    localStorage.setItem(MCP_CONFIG_KEY, JSON.stringify(config));
  }, [config]);

  const connect = async () => {
    const url = config.url.trim();
    if (!url || connecting) return;
    setConnecting(true);
    setResult(null);
    setResult(await connectMCP(url));
    setConnecting(false);
  };

  // 开关打开后自动连接一次
  useEffect(() => {
    if (config.enabled && justEnabled.current) {
      justEnabled.current = false;
      void connect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.enabled]);

  const toggle = () => {
    const enabled = !config.enabled;
    setConfig((prev) => ({ ...prev, enabled }));
    justEnabled.current = enabled;
    if (!enabled) setResult(null);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6 text-center">
        <h1 className="flex items-center justify-center gap-2 text-2xl font-semibold text-gray-900">
          <Plug className="h-6 w-6 text-blue-600" /> MCP 服务接入
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          在页面上配置 Model Context Protocol 服务，启用后连接并查看可用工具
        </p>
      </header>

      {/* 开关 + 地址配置 */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-base font-semibold text-gray-900">启用 MCP 接入</div>
            <p className="mt-1 text-sm text-gray-500">
              开关打开后自动连接下方地址的 MCP 服务，并拉取工具清单
            </p>
          </div>
          <button
            role="switch"
            aria-checked={config.enabled}
            onClick={toggle}
            title={config.enabled ? "关闭 MCP 接入" : "开启 MCP 接入"}
            className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
              config.enabled ? "bg-blue-600" : "bg-gray-200"
            }`}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
                config.enabled ? "left-[22px]" : "left-0.5"
              }`}
            />
          </button>
        </div>

        {config.enabled && (
          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                MCP 服务地址（streamable-http）
              </label>
              <input
                value={config.url}
                onChange={(e) => setConfig((prev) => ({ ...prev, url: e.target.value }))}
                placeholder="http://127.0.0.1:8899/mcp"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 outline-none transition-colors placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </div>

            <div className="flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3">
              <span className="min-w-0 truncate text-sm text-gray-600">
                {connecting ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" /> 正在连接…
                  </span>
                ) : result ? (
                  result.ok ? (
                    <span className="inline-flex items-center gap-1.5 text-green-600">
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                      <span className="truncate">
                        已连接{result.serverName ? ` · ${result.serverName}` : ""} · {result.tools.length} 个工具
                      </span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-red-500">
                      <XCircle className="h-4 w-4 shrink-0" />
                      <span className="truncate">连接失败：{result.error}</span>
                    </span>
                  )
                ) : (
                  "尚未连接"
                )}
              </span>
              <Button
                onClick={() => void connect()}
                loading={connecting}
                disabled={!config.url.trim()}
                size="sm"
              >
                连接
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 工具清单 */}
      <div className="mt-4 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-3 text-base font-semibold text-gray-900">可用工具</div>
        {!config.enabled ? (
          <p className="text-sm text-gray-400">请先开启 MCP 接入开关，连接后这里会展示工具清单。</p>
        ) : connecting ? (
          <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin" /> 正在获取工具清单…
          </div>
        ) : result && result.ok ? (
          result.tools.length > 0 ? (
            <div className="grid gap-2 md:grid-cols-2">
              {result.tools.map((t: MCPToolInfo) => (
                <div
                  key={t.name}
                  className="rounded-xl border border-gray-100 bg-gray-50/60 px-3 py-2.5"
                >
                  <div className="flex items-center gap-1.5 font-mono text-sm text-gray-800">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-500" />
                    {t.name}
                  </div>
                  {t.description && (
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-gray-500">
                      {t.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">该服务暂未暴露任何工具。</p>
          )
        ) : result ? (
          <p className="text-sm text-gray-400">连接未成功，无法获取工具清单。</p>
        ) : (
          <p className="text-sm text-gray-400">等待连接…</p>
        )}
      </div>

      {/* 使用说明 */}
      <div className="mt-4 rounded-2xl border border-gray-200 bg-white p-5 text-sm leading-relaxed text-gray-600 shadow-sm">
        <div className="mb-2 text-base font-semibold text-gray-900">使用说明</div>
        <p className="text-gray-500">本项目的 MCP 服务为独立进程（app/mcp/），streamable-http 端点挂载在 /mcp 路径，默认地址即上方的 127.0.0.1:8899/mcp。启动方式：</p>
        <pre className="mt-2 overflow-x-auto rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-700">
{`# 先启动赛事后端（端口 8000）
uv run uvicorn main:app --reload

# 再以 streamable-http 模式启动 MCP 服务
uv run python -m app.mcp.server --transport streamable-http --host 127.0.0.1 --port 8899`}
        </pre>
        <p className="mt-3 text-xs text-gray-400">
          提示：浏览器跨域访问需 MCP 服务端允许 CORS；接入第三方 MCP 服务时请填写对应地址。
          此页面只做连接与工具展示，问数主链路仍由「问数助手」页面的后端 SSE 提供。
        </p>
      </div>
    </div>
  );
}
