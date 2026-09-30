/** 登录页：手机号 + 密码（新用户自动注册）；系统首次启动时提供超管初始化入口。 */

import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, KeyRound, Shield, Trophy } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ApiError, authApi, setToken, type BootstrapStatus } from "../lib/api";
import { Button, ErrorBanner, Input } from "../components/ui";

type Mode = "login" | "bootstrap";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("login");
  const [bootstrap, setBootstrap] = useState<BootstrapStatus | null>(null);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [bootstrapCode, setBootstrapCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const from =
    (location.state as { from?: string } | null)?.from ??
    new URLSearchParams(location.search).get("redirect") ??
    "/";

  // 首次启动引导：查询系统是否需要初始化超管
  useEffect(() => {
    authApi
      .bootstrapStatus()
      .then(setBootstrap)
      .catch(() => setBootstrap(null));
  }, []);

  const submitLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!/^1\d{10}$/.test(phone)) {
      setError("请输入有效的 11 位手机号");
      return;
    }
    if (password.length < 6 || password.length > 64) {
      setError("密码长度需为 6-64 位");
      return;
    }
    setLoading(true);
    try {
      await login(phone, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登录失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const submitBootstrap = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!bootstrapCode.trim()) {
      setError("请输入初始化码");
      return;
    }
    if (!/^1\d{10}$/.test(phone)) {
      setError("请输入有效的 11 位手机号");
      return;
    }
    if (password.length < 6 || password.length > 64) {
      setError("密码长度需为 6-64 位");
      return;
    }
    setLoading(true);
    try {
      const data = await authApi.bootstrap(bootstrapCode.trim(), phone, password);
      setToken(data.token);
      navigate("/admin/users", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "初始化失败，请检查初始化码");
    } finally {
      setLoading(false);
    }
  };

  const enterBootstrap = () => {
    setError("");
    setMode("bootstrap");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center">
          {mode === "bootstrap" ? (
            <Shield className="h-10 w-10 text-blue-600" />
          ) : (
            <Trophy className="h-10 w-10 text-blue-600" />
          )}
          <h1 className="mt-3 text-xl font-semibold">
            {mode === "bootstrap" ? "系统初始化 · 创建超级管理员" : "赛事官网"}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {mode === "bootstrap"
              ? "首次启动需使用初始化码创建系统超级管理员"
              : "手机号 + 密码登录 · 新用户自动注册"}
          </p>
        </div>

        {mode === "login" && bootstrap?.need_bootstrap && (
          <button
            onClick={enterBootstrap}
            className="mb-4 flex w-full items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-left text-sm text-amber-800 transition-colors hover:bg-amber-100"
          >
            <KeyRound className="h-5 w-5 shrink-0" />
            <span>
              <span className="block font-medium">系统尚未创建超级管理员</span>
              <span className="text-xs text-amber-700">
                初始化码：{bootstrap.code ?? "（见服务启动日志）"} · 点击进入初始化
              </span>
            </span>
          </button>
        )}

        <form
          onSubmit={mode === "bootstrap" ? submitBootstrap : submitLogin}
          className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          {mode === "bootstrap" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">初始化码</label>
              <Input
                value={bootstrapCode}
                onChange={(e) => setBootstrapCode(e.target.value.toUpperCase())}
                placeholder="服务启动日志中的 6 位初始化码"
                autoFocus
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">手机号</label>
            <Input
              type="tel"
              maxLength={11}
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
              placeholder="请输入 11 位手机号"
              autoFocus={mode === "login"}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">密码</label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                maxLength={64}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码（6-64 位）"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                aria-label={showPassword ? "隐藏密码" : "显示密码"}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          {error && <ErrorBanner message={error} />}
          <Button type="submit" loading={loading} className="w-full">
            {mode === "bootstrap" ? "创建超级管理员" : "登录 / 注册"}
          </Button>
          {mode === "bootstrap" && (
            <button
              type="button"
              onClick={() => {
                setError("");
                setMode("login");
              }}
              className="w-full text-center text-xs text-gray-400 hover:text-gray-600"
            >
              返回普通登录
            </button>
          )}
          {mode === "login" && (
            <p className="text-center text-xs text-gray-400">
              新用户输入手机号 + 密码即自动注册；登录后即可报名赛事，创建过赛事的用户自动成为该赛事办赛者
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
