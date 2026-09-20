/** 路由守卫：未登录跳转登录页。 */

import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Spinner } from "../components/ui";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner text="加载用户信息…" />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
