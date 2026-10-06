
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
import { useLegalDocument } from "../hooks/useLegalDocument";

const DOC_MAP = {
  agb: "AGB",
  datenschutz: "DSE",
  kriterien: "F",
  impressum: "IMPRESSUM",
} as const;

type DocParam = keyof typeof DOC_MAP;

export default function LegalPage() {
  const { t } = useTranslation();
  const { doc } = useParams<{ doc: string }>();
  const navigate = useNavigate();
  const location = useLocation();


  const goBack = () =>
    location.key === "default" ? navigate("/") : navigate(-1);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && goBack();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);

  if (!doc || !(doc in DOC_MAP)) return <Navigate to="/" replace />;

  const currentDocKey = doc as DocParam;
  const legalCode = DOC_MAP[currentDocKey]; // тип: "AGB" | "DSE" | "F" | "IMPRESSUM"
  const { data: legalData, loading } = useLegalDocument(legalCode);
  return (
    <Paper elevation={8} sx={{ p: { xs: 2.5, sm: 4.5 }, maxWidth: 800, mx: "auto", borderRadius: 3, my: 4 }}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h5" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
            {legalData?.title || t(`legal.${currentDocKey}`)}
          </Typography>
          <IconButton edge="end" aria-label={t("legal.close", "Schließen")} onClick={goBack}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Divider />

        {currentDocKey === "kriterien" ? (
          <Stack spacing={2.5}>
            <Box sx={{ borderLeft: "4px solid #17407a", bgcolor: "#f8fafc", p: 2.5, borderRadius: 1 }}>
              <Typography variant="body1" sx={{ fontWeight: 600, color: "#0b2142", lineHeight: 1.6 }} lang="de">
                „{legalData?.body || t("legal.criteriaStatement", "Wir wählen Profile ausschließlich anhand der von Ihnen angegebenen Kriterien (Branche, Stadium, Region, Volumen). Es gibt keine bezahlten Platzierungen und keine Bewertung durch einen Score.")}“
              </Typography>
            </Box>

            <Typography variant="body2" color="text.secondary">
              {t("legal.criteriaIntro", "Start Share arbeitet nach dem Prinzip der vollständigen algorithmischen Neutralität (DSA Art. 27).")}
            </Typography>

            <Typography variant="subtitle2" sx={{ fontWeight: 700, mt: 1 }}>
              {t("legal.criteriaParamsTitle", "Hauptparameter für den Match:")}
            </Typography>

            <Stack spacing={1}>
              {[
                ["legal.paramSector", "Branche (Sektor)"],
                ["legal.paramStage", "Finanzierungsstadium (Stage)"],
                ["legal.paramRegion", "Zielregion"],
                ["legal.paramTicket", "Ticketgröße / Kapitalbedarf"],
              ].map(([key, fallback]) => (
                <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <CheckCircleOutlinedIcon color="primary" fontSize="small" />
                  <Typography variant="body2"><strong>{t(key, fallback)}</strong></Typography>
                </Box>
              ))}
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
          <Box>
            {loading ? (
              <Typography variant="body2" color="text.secondary">
                {t("common.loading", "Wird geladen…")}
              </Typography>
            ) : legalData?.body ? (
              <Typography
                variant="body1"
                lang="de"
                sx={{ whiteSpace: "pre-line", lineHeight: 1.7, color: "#1e293b" }}
              >
                {legalData.body}
              </Typography>
            ) : (
              <Alert severity="info">{t("legal.placeholder", "In Vorbereitung...")}</Alert>
            )}
          </Box>
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
