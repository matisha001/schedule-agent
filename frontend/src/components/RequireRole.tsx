/** 角色守卫：允许指定角色访问；未登录或角色不符时跳转。 */

import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Spinner } from "./ui";

export default function RequireRole({
  roles,
  children,
  fallback = "/",
}: {
  roles: string[];
  children: React.ReactNode;
  fallback?: string;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner text="加载用户信息…" />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (!roles.includes(user.role ?? "")) {
    return <Navigate to={fallback} replace />;
  }
  return <>{children}</>;
}
