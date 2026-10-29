import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { HomeRedirect, PublicOnly, RequireRole } from "./auth/guards";
import Layout from "./components/Layout";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import FeedPage from "./investor/FeedPage";
import LegalPage from "./pages/LegalPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import StaffLayout from "./staff/StaffLayout";
import StaffUsersPage from "./staff/UsersPage";
import StaffConsentsPage from "./staff/ConsentsPage";
import StaffEventsPage from "./staff/EventsPage";
import StaffModerationPage from "./staff/ModerationPage";
import StaffLegalDocsPage from "./staff/StaffLegalDocsPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import CompanyPage from "./profile/CompanyPage";
import ProfileLayout from "./profile/ProfileLayout";
import OverviewPage from "./profile/OverviewPage";
import DeckPage from "./profile/DeckPage";
import IntrosPage from "./profile/IntrosPage";
import TeaserSectionPage from "./profile/TeaserSectionPage";
import InvestorLayout from "./investor/InvestorLayout";
import MandatePage from "./investor/MandatePage";
import PrivacyPage from "./components/PrivacyPage";
import StaffConfigPage from "./staff/StaffConfigPage";
import InvestorProfilePage from "./investor/InvestorProfilePage";

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

    <Route path="/staff/dashboard" element={<RequireRole role="staff"><StaffLayout /></RequireRole>}>
      <Route index element={<StaffModerationPage />} />
      <Route path="users" element={<StaffUsersPage />} />
      <Route path="consents" element={<StaffConsentsPage />} />
      <Route path="events" element={<StaffEventsPage />} />
      <Route path="config" element={<StaffConfigPage />} />
      <Route path="legal" element={<StaffLegalDocsPage />} />
    </Route>

        {/* 1. ПОТІК СТАРТАПУ: Анкета + Завантаження деку + Редактор тизера ШІ (все в ProfilePage) */}
        <Route path="/profile" element={<RequireRole role="startup"><ProfileLayout /></RequireRole>}>
          <Route index element={<OverviewPage />} />
          <Route path="company" element={<CompanyPage />} />
          <Route path="deck" element={<DeckPage />} />
          <Route path="teaser" element={<TeaserSectionPage />} />
          <Route path="intros" element={<IntrosPage />} />
          <Route path="privacy" element={<PrivacyPage audience="startup" />} />
        </Route>

        {/* 2. ПОТІК ІНВЕСТОРА: */}
        <Route path="/investor" element={<RequireRole role="investor"><InvestorLayout /></RequireRole>}>
          <Route index element={<MandatePage />} />
          <Route path="feed" element={<FeedPage />} />
          <Route path="profile" element={<InvestorProfilePage />} />
          <Route path="privacy" element={<PrivacyPage audience="investor" />} />
        </Route>

        {/* Редирект на головну для всіх неіснуючих сторінок */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
