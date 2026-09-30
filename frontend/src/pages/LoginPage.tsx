/** 登录页：手机号 + 密码（新用户自动注册并设置密码）。 */

import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Trophy } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Button, ErrorBanner, Input } from "../components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const from =
    (location.state as { from?: string } | null)?.from ??
    new URLSearchParams(location.search).get("redirect") ??
    "/";

  const submit = async (e: FormEvent) => {
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center">
          <Trophy className="h-10 w-10 text-blue-600" />
          <h1 className="mt-3 text-xl font-semibold">赛事官网</h1>
          <p className="mt-1 text-sm text-gray-500">手机号 + 密码登录 · 新用户自动注册</p>
        </div>
        <form
          onSubmit={submit}
          className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">手机号</label>
            <Input
              type="tel"
              maxLength={11}
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))}
              placeholder="请输入 11 位手机号"
              autoFocus
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
            登录 / 注册
          </Button>
          <p className="text-center text-xs text-gray-400">
            新用户输入手机号 + 密码即自动注册；登录后即可报名赛事，创建过赛事的用户自动成为该赛事办赛者
          </p>
        </form>
      </div>
    </div>
  );
}
