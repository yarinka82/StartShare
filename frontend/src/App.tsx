import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { HomeRedirect, PublicOnly, RequireRole } from "./auth/guards";
import Layout from "./components/Layout";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import InvestorFeedPage from "./pages/InvestorFeedPage";
import InvestorHomePage from "./pages/InvestorHomePage";
import LegalPage from "./pages/LegalPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";

export default function App() {
  return (
    <Routes>
      {/* Signed-out screens: full-screen split layout (FormCard), no app bar / container / footer around it */}
      <Route element={<Outlet />}>
        <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
        <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
      </Route>

      {/* Авторизована зона платформи (з шапкою AppBar, перемикачем мов і футером) */}
      <Route element={<Layout />}>
        <Route path="/" element={<HomeRedirect />} />

        {/* Юридичні сторінки (AGB, Datenschutz, Impressum, Kriterien / Текст F) */}
        <Route path="/legal/:doc" element={<LegalPage />} />

        {/* 1. ПОТІК СТАРТАПУ: Анкета + Завантаження деку + Редактор тизера ШІ (все в ProfilePage) */}
        <Route
          path="/profile"
          element={
            <RequireRole role="startup">
              <ProfilePage />
            </RequireRole>
          }
        />

        {/* 2. ПОТІК ІНВЕСТОРА: */}
        {/* а) Налаштування мандату та підтвердження статусу B2B (Текст C) */}
        <Route
          path="/investor"
          element={
            <RequireRole role="investor">
              <InvestorHomePage />
            </RequireRole>
          }
        />
        {/* б) Стрічка підібраних тизерів зі сліпими картками (BlindTeaserCard + Текст B) */}
        <Route
          path="/investor/feed"
          element={
            <RequireRole role="investor">
              <InvestorFeedPage />
            </RequireRole>
          }
        />

        {/* Редирект на головну для всіх неіснуючих сторінок */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
