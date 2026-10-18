import { Box, Link, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import { FOOTER_HEIGHT } from "./footerConfig";

const DOCS = ["agb", "datenschutz", "impressum", "kriterien"] as const;

/**
 * Slim legal bar pinned to the bottom of the viewport.
 * variant="app"  – light blue bar for signed-in screens
 * variant="auth" – translucent white bar over the login / photo backgrounds
 */
export default function AppFooter({ variant = "app" }: { variant?: "app" | "auth" }) {
  const { t } = useTranslation();
  const auth = variant === "auth";

  return (
    <Box
      component="footer"
      sx={{
        position: "fixed", left: 0, right: 0, bottom: 0,
        zIndex: (theme) => theme.zIndex.appBar,
        height: FOOTER_HEIGHT, px: 2,
        display: "flex", alignItems: "center", justifyContent: "center",
        columnGap: { xs: 2, sm: 3 }, whiteSpace: "nowrap", overflowX: "auto",
        bgcolor: auth ? "rgba(255,255,255,0.9)" : "#eef3fb",
        backdropFilter: auth ? "blur(6px)" : undefined,
        borderTop: "1px solid", borderColor: auth ? "divider" : "#d6e2f5",
      }}
    >
      {DOCS.map((doc) => (
        <Link key={doc} component={RouterLink} to={`/legal/${doc}`} variant="caption" underline="hover" sx={{ color: "text.secondary" }}>
          {t(`footer.${doc}`)}
        </Link>
      ))}
      <Typography variant="caption" sx={{ color: "text.secondary", opacity: 0.8, display: { xs: "none", sm: "inline" } }}>
        © {new Date().getFullYear()} {t("app.name")}
      </Typography>
    </Box>
  );
}