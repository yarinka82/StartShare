
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CloseIcon from "@mui/icons-material/Close";
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";

// 1. Додаємо 'kriterien' (Текст F) у список дозволених документів
const DOCS = ["agb", "datenschutz", "impressum", "kriterien"] as const;
type Doc = (typeof DOCS)[number];

export default function LegalPage() {
  const { t } = useTranslation();
  const { doc } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const goBack = () => (location.key === "default" ? navigate("/") : navigate(-1));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && goBack();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);

  if (!DOCS.includes(doc as Doc)) return <Navigate to="/" replace />;

  const currentDoc = doc as Doc;

  return (
    <Paper elevation={8} sx={{ p: { xs: 2.5, sm: 4.5 }, maxWidth: 800, mx: "auto", borderRadius: 3 }}>
      <Stack spacing={3}>
        {/* Шапка модального вікна */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h5" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
            {t(`legal.${currentDoc}`)}
          </Typography>
          <IconButton edge="end" aria-label={t("legal.close", "Schließen")} onClick={goBack}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Divider />

        {/* СПЕЦІАЛЬНИЙ КОНТЕНТ ДЛЯ ТЕКСТУ F (КРИТЕРІЇ ВІДБОРУ) */}
        {currentDoc === "kriterien" ? (
          <Stack spacing={2.5}>
            {/* Офіційне юридичне формулювання (Текст F) */}
            <Box sx={{ borderLeft: "4px solid #17407a", bgcolor: "#f8fafc", p: 2.5, borderRadius: 1 }}>
              <Typography variant="body1" sx={{ fontWeight: 600, color: "#0b2142", lineHeight: 1.6 }} lang="de">
                „Wir wählen Profile ausschließlich anhand der von Ihnen angegebenen Kriterien (Branche, Stadium, Region, Volumen). Es gibt keine bezahlten Platzierungen und keine Bewertung durch einen Score.“
              </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary">
              {t("legal.criteriaIntro", "Start Share arbeitet nach dem Prinzip der vollständigen algorithmischen Neutralität (DSA Art. 27).")}
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mt: 1 }}>
              {t("legal.criteriaParamsTitle", "Hauptparameter für den Match:")}
            </Typography>

            <Stack spacing={1}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CheckCircleOutlinedIcon color="primary" fontSize="small" />
                <Typography variant="body2"><strong>{t("legal.paramSector", "Branche (Sektor)")}</strong></Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CheckCircleOutlinedIcon color="primary" fontSize="small" />
                <Typography variant="body2"><strong>{t("legal.paramStage", "Finanzierungsstadium (Stage)")}</strong></Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CheckCircleOutlinedIcon color="primary" fontSize="small" />
                <Typography variant="body2"><strong>{t("legal.paramRegion", "Zielregion")}</strong></Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CheckCircleOutlinedIcon color="primary" fontSize="small" />
                <Typography variant="body2"><strong>{t("legal.paramTicket", "Ticketgröße / Kapitalbedarf")}</strong></Typography>
              </Box>
            </Stack>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mt: 1 }}>
              {t("legal.criteriaExcludedTitle", "Ausdrücklich ausgeschlossen:")}
            </Typography>

            <Stack spacing={1}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <BlockIcon color="error" fontSize="small" />
                <Typography variant="body2">{t("legal.noPaid", "Keine bezahlten Platzierungen oder hervorgehobene Listings.")}</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <BlockIcon color="error" fontSize="small" />
                <Typography variant="body2">{t("legal.noScore", "Keine undurchsichtige KI-Erfolgsbewertung (kein Scoring).")}</Typography>
              </Box>
            </Stack>
          </Stack>
        ) : (
          /* ДЛЯ AGB, DATENSCHUTZ, IMPRESSUM (Поки фінальні тексти готуються юристом) */
          <Alert severity="info">{t("legal.placeholder")}</Alert>
        )}

        <Box sx={{ pt: 1 }}>
          <Button variant="contained" onClick={goBack} sx={{ bgcolor: "#17407a", "&:hover": { bgcolor: "#0b2142" } }}>
            {t("legal.back", "Zurück")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
