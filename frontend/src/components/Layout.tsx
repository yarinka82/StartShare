import LogoutIcon from "@mui/icons-material/Logout";
import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { useAuth } from "../auth/AuthContext";
import AuthBackground from "./AuthBackground";
import LanguageSwitcher from "./LanguageSwitcher";
import AppFooter from "./AppFooter";
import { FOOTER_HEIGHT } from "./footerConfig";

export default function Layout() {
  const { t } = useTranslation();
  const { user, loading, logout } = useAuth();
  const signedOut = !loading && !user;
  const { pathname } = useLocation();
  const wide = pathname.startsWith("/profile");
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", pb: `${FOOTER_HEIGHT}px`, bgcolor: wide ? "grey.100" : "background.default", position: "relative", display: "flex", flexDirection: "column" }}>
      {signedOut && <AuthBackground />}

      <AppBar position="relative" elevation={0} sx={{ zIndex: 1, ...(signedOut && { bgcolor: "transparent" }) }}>
        <Toolbar sx={{ gap: 2 }}>
          {/* 1. Логотип / Назва — тепер закривається одразу */}
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{ color: "inherit", textDecoration: "none", fontWeight: 800, letterSpacing: -0.5 }}
          >
            {t("app.name")}
          </Typography>

          {/* 2. Блок навігації між логотипом та мовами (займає вільний простір) */}
          <Box sx={{ flexGrow: 1, display: "flex", gap: 1, ml: 2 }}>
            {/* Навігація для інвестора */}
            {user?.role === "investor" && (
              <>
                <Button
                  component={RouterLink}
                  to="/investor/feed"
                  color="inherit"
                  sx={{ textTransform: "none", fontWeight: 600 }}
                >
                  {t("nav.digest", "Дайджест")}
                </Button>
                <Button
                  component={RouterLink}
                  to="/investor"
                  color="inherit"
                  sx={{ textTransform: "none" }}
                >
                  {t("nav.mandate", "Мандат")}
                </Button>
              </>
            )}

            {/* Навігація для стартапу */}
            {user?.role === "startup" && (
              <Button
                component={RouterLink}
                to="/profile"
                color="inherit"
                sx={{ textTransform: "none", fontWeight: 600 }}
              >
                {t("nav.profile", "Мій профіль")}
              </Button>
            )}
          </Box>

            {user?.role === "staff" && (
              <Button
                component={RouterLink}
                to="/staff/dashboard"
                color="error"
                startIcon={<AdminPanelSettingsIcon />}
                sx={{ textTransform: "none", fontWeight: 700 }}
              >
                {t("nav.staffPanel", "Адмін-панель")}
              </Button>
            )}

          {/* 3. Перемикач мов */}
          <LanguageSwitcher />

          {/* 4. Кнопка виходу */}
          {user && (
            <Button
              color="inherit"
              startIcon={<LogoutIcon />}
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              sx={{ textTransform: "none" }}
            >
              {t("nav.logout")}
            </Button>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth={wide ? "lg" : "md"} sx={{ py: { xs: 3, md: 5 }, position: "relative", zIndex: 1, flexGrow: 1 }}>
        <Outlet />
      </Container>

      {/* Обов'язковий юридичний футер */}
      <AppFooter variant={signedOut ? "auth" : "app"} />
    </Box>
  );
}