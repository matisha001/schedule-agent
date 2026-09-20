/** 路由：官网（玩家视角）与管理后台（办赛者视角）双入口。 */

import { Navigate, Route, Routes } from "react-router-dom";
import { AdminLayout, PortalLayout } from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import LoginPage from "./pages/LoginPage";
import TournamentListPage from "./pages/portal/TournamentListPage";
import TournamentDetailPage from "./pages/portal/TournamentDetailPage";
import MyTournamentsPage from "./pages/portal/MyTournamentsPage";
import AskPage from "./pages/portal/AskPage";
import AdminTournamentsPage from "./pages/admin/AdminTournamentsPage";
import AdminTournamentDetailPage from "./pages/admin/AdminTournamentDetailPage";

export default function App() {
  return (
    <Routes>
      {/* 登录 */}
      <Route path="/login" element={<LoginPage />} />

      {/* 官网（玩家视角） */}
      <Route element={<PortalLayout />}>
        <Route index element={<TournamentListPage />} />
        <Route path="tournaments/:id" element={<TournamentDetailPage />} />
        {/* 报名链接直达：/register/:id → 详情页并自动打开报名 */}
        <Route path="register/:id" element={<TournamentDetailPage />} />
        <Route
          path="my"
          element={
            <RequireAuth>
              <MyTournamentsPage />
            </RequireAuth>
          }
        />
        <Route path="ask" element={<AskPage />} />
      </Route>

      {/* 管理后台（办赛者视角） */}
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<AdminTournamentsPage />} />
        <Route path="tournaments/:id" element={<AdminTournamentDetailPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
