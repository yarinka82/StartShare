import { Box, Link, Stack, Typography, useMediaQuery, useTheme } from "@mui/material";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";

import LanguageSwitcher from "./LanguageSwitcher";

interface FormCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

const LEGAL = ["impressum", "datenschutz", "agb"] as const;

/**
 * Full-screen split layout for signed-out pages: form on the left, promo on the right.
 * Must be rendered WITHOUT the app chrome (see App.tsx), otherwise 100dvh + app bar overflows the screen.
 */
export default function FormCard({ title, subtitle, children }: FormCardProps) {
  const { t } = useTranslation();
  const theme = useTheme();
  const isLgUp = useMediaQuery(theme.breakpoints.up("lg"));

  return (
    <Box sx={{ minHeight: "100dvh", display: "flex", alignItems: "flex-start", bgcolor: "#f8fafc" }}>
      {/* LEFT: form column. Exactly one screen high; if the form is longer, the page scrolls. */}
      <Box
        sx={{
          flex: { xs: "1 1 100%", lg: "0 0 500px", xl: "0 0 560px" },
          minHeight: "100dvh",
          display: "flex",
          flexDirection: "column",
          p: { xs: 3, sm: 4 },
          bgcolor: "background.paper",
          zIndex: 2,
          boxShadow: { xs: "none", lg: "10px 0 30px rgba(0,0,0,0.04)" },
        }}
      >
        {/* Brand + the single language switcher */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, flexWrap: "wrap", mb: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Box
              sx={{
                width: 36, height: 36, borderRadius: 1.5, bgcolor: "#17407a", color: "#f4c95d",
                display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "1.2rem",
              }}
            >
              S
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 800, color: "#0b2142", letterSpacing: -0.5 }}>
              Start Share
            </Typography>
            <Box
              component="span"
              sx={{
                fontSize: "0.7rem", bgcolor: "#f1f5f9", color: "#475569", px: 1, py: 0.2,
                borderRadius: 1, border: "1px solid #e2e8f0", fontWeight: 600,
              }}
            >
              {t("authPromo.marketTag")}
            </Box>
          </Box>
          <LanguageSwitcher onDark={false} />
        </Box>

        {/* Form (LoginPage, RegisterPage, ...) is centered in the free space */}
        <Box sx={{ maxWidth: 420, width: "100%", mx: "auto", my: "auto", py: 2 }}>
          <Typography variant="h5" component="h1" sx={{ fontWeight: 700, color: "#0f172a", mb: 1 }}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              {subtitle}
            </Typography>
          )}
          {/* Stack: pages pass several blocks (alert + form + button); this keeps them evenly spaced */}
          <Stack spacing={2} sx={{ mt: 2 }}>{children}</Stack>
        </Box>

        {/* Single footer for all screen sizes: legal links + copyright */}
        <Box component="footer" sx={{ mt: 2, pt: 2, borderTop: "1px solid #f1f5f9", textAlign: "center" }}>
          <Box sx={{ display: "flex", justifyContent: "center", flexWrap: "wrap", columnGap: 3, rowGap: 0.5 }}>
            {LEGAL.map((doc) => (
              <Link
                key={doc}
                component={RouterLink}
                to={`/legal/${doc}`}
                target="_blank"
                rel="noopener"
                variant="caption"
                underline="hover"
                sx={{ color: "text.secondary" }}
              >
                {t(`footer.${doc}`)}
              </Link>
            ))}
          </Box>
          <Typography variant="caption" sx={{ display: "block", mt: 0.5, color: "text.disabled" }}>
            © {new Date().getFullYear()} {t("authPromo.copyright")}
          </Typography>
        </Box>
      </Box>

      {/* RIGHT: promo. Sticky, so it stays in view when the form column scrolls. */}
      {isLgUp && (
        <Box
          sx={{
            flex: 1,
            position: "sticky",
            top: 0,
            height: "100dvh",
            backgroundImage: "url('/auth-bg.svg')",
            backgroundSize: "cover",
            backgroundPosition: "center",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 4,
            p: 8,
            color: "#ffffff",
          }}
        >
          <Box>
            <Box
              sx={{
                display: "inline-block", px: 2, py: 0.6, borderRadius: 5,
                bgcolor: "rgba(255, 255, 255, 0.12)", backdropFilter: "blur(10px)",
                border: "1px solid rgba(255, 255, 255, 0.2)", fontSize: "0.8rem", fontWeight: 600, color: "#f4c95d",
              }}
            >
              {t("authPromo.badge")}
            </Box>
          </Box>

          <Box sx={{ maxWidth: 540 }}>
            <Typography variant="h3" sx={{ fontWeight: 800, lineHeight: 1.25, mb: 2 }}>
              {t("authPromo.heroTitle")}
            </Typography>
            <Typography variant="body1" sx={{ color: "rgba(235, 245, 255, 0.85)", lineHeight: 1.6 }}>
              {t("authPromo.heroSubtitle")}
            </Typography>
            <Box
              sx={{
                display: "flex", flexWrap: "wrap", gap: 3, mt: 4, pt: 3,
                borderTop: "1px solid rgba(255,255,255,0.15)", fontSize: "0.85rem", color: "rgba(255,255,255,0.8)",
              }}
            >
              <Box>✓ {t("authPromo.featureDsa")}</Box>
              <Box>✓ {t("authPromo.featureB2B")}</Box>
              <Box>✓ {t("authPromo.featureServers")}</Box>
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  );
}
