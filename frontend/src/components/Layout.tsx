import LogoutIcon from "@mui/icons-material/Logout";
import { AppBar, Box, Button, Container, Link, Toolbar, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import AuthBackground from "./AuthBackground";
import LanguageSwitcher from "./LanguageSwitcher";

export default function Layout() {
  const { t } = useTranslation();
  const { user, loading, logout } = useAuth();
  const signedOut = !loading && !user;
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", position: "relative", display: "flex", flexDirection: "column" }}>
      {signedOut && <AuthBackground />}
      <AppBar position="relative" elevation={0} sx={{ zIndex: 1, ...(signedOut && { bgcolor: "transparent" }) }}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" component={RouterLink} to="/" sx={{ flexGrow: 1, color: "inherit", textDecoration: "none" }}>
            {t("app.name")}
          </Typography>
          <LanguageSwitcher />
          {user && (
            <Button
              color="inherit"
              startIcon={<LogoutIcon />}
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              {t("nav.logout")}
            </Button>
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: { xs: 3, md: 5 }, position: "relative", zIndex: 1, flexGrow: 1 }}>
        <Outlet />
      </Container>
        <Box
          component="footer"
          sx={{
            position: "relative",
            zIndex: 1,
            py: 2,
            textAlign: "center",
            display: "flex",
            justifyContent: "center",
            flexWrap: "wrap",
            gap: 3,
          }}
        >
          {(["agb", "datenschutz", "impressum", "kriterien"] as const).map((doc) => (
            <Link
              key={doc}
              component={RouterLink}
              to={`/legal/${doc}`}
              variant="caption"
              underline="hover"
              sx={{ color: signedOut ? "rgba(255,255,255,0.8)" : "text.secondary" }}
            >
              {t(`footer.${doc}`)}
            </Link>
          ))}
        </Box>
    </Box>
  );
}
