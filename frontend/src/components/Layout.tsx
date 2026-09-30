/** 页面布局：官网（玩家视角）与管理后台（办赛者视角），两个独立入口。 */

import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ClipboardList, LayoutDashboard, LogOut, MessageSquareText, Plug, Settings, Shield, Trophy, Users } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ROLE_LABELS } from "../types";

function navCls({ isActive }: { isActive: boolean }) {
  return `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? "bg-blue-50 text-blue-600" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
  }`;
}

function HeaderRight() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const canAdmin = user && ["organizer", "operator", "super_admin"].includes(user.role ?? "");
  return (
    <div className="flex items-center gap-2">
      {canAdmin && (
        <Link
          to="/admin"
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          <LayoutDashboard className="h-4 w-4" /> 管理后台
        </Link>
      )}
      {user ? (
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-gray-600">
            {user.nickname}
            {user.role && user.role !== "player" && (
              <span className="ml-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                {ROLE_LABELS[user.role] ?? user.role}
              </span>
            )}
          </span>
          <Link
            to="/account"
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
            title="账号设置"
          >
            <Settings className="h-4 w-4" />
          </Link>
          <button
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
            title="退出登录"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <Link
          to="/login"
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          登录
        </Link>
      )}
    </div>
  );
}

/** 官网布局（玩家视角） */
export function PortalLayout() {
  const location = useLocation();
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-blue-600" />
            <span className="text-base font-semibold">赛事官网</span>
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navCls}>
              赛事广场
            </NavLink>
            <NavLink to="/my" className={navCls}>
              我的比赛
            </NavLink>
            <NavLink to="/ask" className={navCls}>
              <span className="inline-flex items-center gap-1">
                <MessageSquareText className="h-3.5 w-3.5" /> 问数助手
              </span>
            </NavLink>
            <NavLink to="/mcp" className={navCls}>
              <span className="inline-flex items-center gap-1">
                <Plug className="h-3.5 w-3.5" /> MCP 服务
              </span>
            </NavLink>
          </nav>
          <HeaderRight />
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet key={location.pathname} />
      </main>
    </div>
  );
}

/** 管理后台布局（办赛者 / 运营 / 超管视角） */
export function AdminLayout() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";
  const canReview = user && ["operator", "super_admin"].includes(user.role ?? "");
  const roleLabel = ROLE_LABELS[user?.role ?? ""] ?? "办赛者";
  return (
    <div className="flex min-h-screen flex-col bg-gray-100">
      <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link to="/admin" className="flex items-center gap-2">
              <LayoutDashboard className="h-5 w-5 text-blue-600" />
              <span className="text-base font-semibold">赛事管理后台</span>
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                {roleLabel}
              </span>
            </Link>
            <nav className="flex items-center gap-1">
              <NavLink to="/admin" end className={navCls}>
                我的赛事
              </NavLink>
              {canReview && (
                <NavLink to="/admin/applications" className={navCls}>
                  <span className="inline-flex items-center gap-1">
                    <ClipboardList className="h-3.5 w-3.5" /> 申请审批
                  </span>
                </NavLink>
              )}
              {isSuperAdmin && (
                <NavLink to="/admin/users" className={navCls}>
                  <span className="inline-flex items-center gap-1">
                    <Shield className="h-3.5 w-3.5" /> 用户管理
                  </span>
                </NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              <Users className="h-4 w-4" /> 返回官网
            </Link>
            {user && <span className="text-sm text-gray-600">{user.nickname}</span>}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
