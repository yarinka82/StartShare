import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import LogoutIcon from "@mui/icons-material/Logout";
import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AppFooter from "./AppFooter";
import AuthBackground from "./AuthBackground";
import { FOOTER_HEIGHT } from "./footerConfig";
import LanguageSwitcher from "./LanguageSwitcher";
import { UnsavedGuardProvider, useGuardedLink, useRequestLeave } from "./UnsavedGuard";

function LayoutShell() {
  const { t } = useTranslation();
  const { user, loading, logout } = useAuth();
  const signedOut = !loading && !user;
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const guardLink = useGuardedLink();
  const requestLeave = useRequestLeave();

  const staffArea = pathname.startsWith("/staff");
  const wide = staffArea || pathname.startsWith("/profile") || pathname.startsWith("/investor");
  const maxWidth = staffArea ? "xl" : wide ? "lg" : "md";

  return (
    <Box
      sx={{
        minHeight: "100vh", pb: `${FOOTER_HEIGHT}px`, bgcolor: wide ? "grey.100" : "background.default",
        position: "relative", display: "flex", flexDirection: "column",
      }}
    >
      {signedOut && <AuthBackground />}

      <AppBar position="relative" elevation={0} sx={{ zIndex: 1, ...(signedOut && { bgcolor: "transparent" }) }}>
        <Toolbar sx={{ gap: 2 }}>
          {/* 1. Logo / name */}
          <Typography
            variant="h6" component={RouterLink} to="/" onClick={guardLink("/")}
            sx={{ color: "inherit", textDecoration: "none", fontWeight: 800, letterSpacing: -0.5 }}
          >
            {t("app.name")}
          </Typography>

          {/* 2. Navigation between the logo and the languages (takes the free space) */}
          <Box sx={{ flexGrow: 1, display: "flex", gap: 1, ml: 2 }}>
            {user?.role === "investor" && (
              <>
                <Button component={RouterLink} to="/investor/profile" onClick={guardLink("/investor/profile")} color="inherit">
                  {t("investor.profile.title", "Профіль інвестора")}
                </Button>
                <Button component={RouterLink} to="/investor" onClick={guardLink("/investor")} color="inherit">
                  {t("nav.mandate", "Мандат")}
                </Button>
                <Button component={RouterLink} to="/investor/feed" onClick={guardLink("/investor/feed")} color="inherit">
                  {t("nav.digest", "Дайджест")}
                </Button>
              </>
            )}

            {user?.role === "startup" && (
              <Button component={RouterLink} to="/profile" onClick={guardLink("/profile")} color="inherit">
                {t("nav.profile", "Мій профіль")}
              </Button>
            )}
          </Box>

          {user?.role === "staff" && (
            <Button
              component={RouterLink} to="/staff/dashboard" onClick={guardLink("/staff/dashboard")}
              color="error" startIcon={<AdminPanelSettingsIcon />} sx={{ fontWeight: 700 }}
            >
              {t("nav.staffPanel", "Адмін-панель")}
            </Button>
          )}

          {/* 3. Language switcher */}
          <LanguageSwitcher />

          {/* 4. Logout (also asks when there are unsaved edits) */}
          {user && (
            <Button
              color="inherit" startIcon={<LogoutIcon />}
              onClick={() =>
                requestLeave(async () => {
                  await logout();
                  navigate("/login");
                })
              }
            >
              {t("nav.logout")}
            </Button>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth={maxWidth} sx={{ py: { xs: 3, md: 5 }, position: "relative", zIndex: 1, flexGrow: 1 }}>
        <Outlet />
      </Container>

      {/* Mandatory legal footer */}
      <AppFooter variant={signedOut ? "auth" : "app"} />
    </Box>
  );
}

export default function Layout() {
  return (
    <UnsavedGuardProvider>
      <LayoutShell />
    </UnsavedGuardProvider>
  );
}