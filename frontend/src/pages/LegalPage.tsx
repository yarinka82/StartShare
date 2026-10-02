import CloseIcon from "@mui/icons-material/Close";
import { Alert, Box, Button, IconButton, Paper, Stack, Typography } from "@mui/material";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";

const DOCS = ["agb", "datenschutz", "impressum"] as const;
type Doc = (typeof DOCS)[number];

/** Placeholder: AGB / Datenschutz / Impressum texts come from legal counsel. */
export default function LegalPage() {
  const { t } = useTranslation();
  const { doc } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // "default" key = the page was opened directly (new tab, bookmark): there is nothing to go back to
  const goBack = () => (location.key === "default" ? navigate("/") : navigate(-1));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && goBack();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);

  if (!DOCS.includes(doc as Doc)) return <Navigate to="/" replace />;

  return (
    <Paper elevation={8} sx={{ p: { xs: 2.5, sm: 4 } }}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
          <Typography variant="h5" component="h1" sx={{ flexGrow: 1 }}>
            {t(`legal.${doc as Doc}`)}
          </Typography>
          <IconButton edge="end" aria-label={t("legal.close")} onClick={goBack}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Alert severity="info">{t("legal.placeholder")}</Alert>
        <Box>
          <Button variant="contained" onClick={goBack}>
            {t("legal.back")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
