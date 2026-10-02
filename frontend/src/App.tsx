import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { HomeRedirect, PublicOnly, RequireRole } from "./auth/guards";
import Layout from "./components/Layout";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
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

      {/* Everything else keeps the app chrome */}
      <Route element={<Layout />}>
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/legal/:doc" element={<LegalPage />} />
        <Route path="/profile" element={<RequireRole role="startup"><ProfilePage /></RequireRole>} />
        <Route path="/investor" element={<RequireRole role="investor"><InvestorHomePage /></RequireRole>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
