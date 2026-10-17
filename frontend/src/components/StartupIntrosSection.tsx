
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import HandshakeIcon from "@mui/icons-material/Handshake";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import {StartupIntroDto} from "../api/types";

export default function StartupIntrosSection() {
  const { t, i18n } = useTranslation();
  const [intros, setIntros] = useState<StartupIntroDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const loadIntros = async () => {
    try {
      setLoading(true);
      const data = await api.getStartupIntros();
      setIntros(data);
    } catch {
      // помилка завантаження
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadIntros();
  }, []);

  const handleRespond = async (id: string, action: "freigabe" | "nein") => {
    try {
      setBusyId(id);
      await api.respondToStartupIntro(id, action);

      // Прибираємо картку зі списку вхідних
      setIntros((prev) => prev.filter((item) => item.id !== id));

      if (action === "freigabe") {
        setToastMsg(
          t(
            "freigabeRequests.freigabeSuccessToast",
            "Контакти успішно відкрито! Обом сторонам надіслано e-mail з контактами та Текстом E."
          )
        );
      } else {
        setToastMsg(t("freigabeRequests.declineSuccessToast", "Запит інвестора відхилено."));
      }
    } catch (e: any) {
      alert(e.message || "Помилка при обробці запиту.");
    } finally {
      setBusyId(null);
    }
  };

  // Якщо запитів немає — нічого не рендеримо, щоб не захаращувати екран
  if (intros.length === 0 && !loading) {
    return null;
  }

  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 800, color: "#166534", display: "flex", alignItems: "center", gap: 1 }}>
        <HandshakeIcon /> {t("freigabeRequests.sectionTitle", "Вхідні запити на знайомство (Freigabe)")}
      </Typography>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : (
        intros.map((item) => (
          <Paper
            key={item.id}
            elevation={2}
            sx={{
              p: { xs: 2.5, sm: 3 },
              borderRadius: 2.5,
              borderLeft: "5px solid #166534",
              bgcolor: "#f0fdf4",
              border: "1px solid #bbf7d0",
            }}
          >
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1, mb: 1.5 }}>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 800, color: "#0f172a" }}>
                  {item.investor_name}
                </Typography>
                <Chip
                  label={item.investor_type}
                  size="small"
                  sx={{ bgcolor: "#dcfce7", color: "#166534", fontWeight: 700, mt: 0.5 }}
                />
              </Box>

              {item.expires_at && (
                <Chip
                  icon={<AccessTimeIcon fontSize="small" />}
                  label={`${t("freigabeRequests.expiresIn", "Діє до")}: ${new Date(item.expires_at).toLocaleDateString(i18n.resolvedLanguage)}`}
                  size="small"
                  variant="outlined"
                  sx={{ color: "#854d0e", borderColor: "#fde047", bgcolor: "#fef9c3" }}
                />
              )}
            </Box>

            {/* Персональне повідомлення інвестора (якщо є) */}
            {item.message && (
              <Box sx={{ p: 2, bgcolor: "#ffffff", borderRadius: 2, border: "1px dashed #86efac", my: 2 }}>
                <Typography variant="caption" sx={{ color: "#64748b", fontWeight: 700, textTransform: "uppercase" }}>
                  {t("freigabeRequests.investorMessageLabel", "Повідомлення від інвестора:")}
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: "italic", color: "#334155", mt: 0.5 }}>
                  «{item.message}»
                </Typography>
              </Box>
            )}

            {/* ЮРИДИЧНИЙ ТЕКСТ D: Застереження про закриті контакти */}
            <Box sx={{ bgcolor: "#ffffff", p: 1.5, borderRadius: 1.5, border: "1px solid #dcfce7", my: 2 }}>
              <Typography variant="caption" sx={{ color: "#475569", display: "block", lineHeight: 1.5 }} lang="de">
                <strong>{item.investor_name}</strong> {t("freigabeRequests.textD", "hat Interesse an Ihrem Profil. Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben.")}
              </Typography>
            </Box>

            {/* КНОПКИ РІШЕННЯ: FREIGABE ТА NEIN */}
            <Stack direction="row" spacing={2} sx={{ pt: 1 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircleIcon />}
                disabled={busyId === item.id}
                onClick={() => handleRespond(item.id, "freigabe")}
                sx={{ bgcolor: "#166534", textTransform: "none", fontWeight: 700, px: 3, "&:hover": { bgcolor: "#14532d" } }}
              >
                {busyId === item.id ? t("common.saving", "Обробка...") : t("freigabeRequests.freigabeBtn", "✓ Freigabe (Відкрити контакти)")}
              </Button>

              <Button
                variant="outlined"
                color="inherit"
                startIcon={<CloseIcon />}
                disabled={busyId === item.id}
                onClick={() => handleRespond(item.id, "nein")}
                sx={{ textTransform: "none", color: "#64748b" }}
              >
                {t("freigabeRequests.declineBtn", "Відхилити")}
              </Button>
            </Stack>
          </Paper>
        ))
      )}

      {/* Тост сповіщення про результат */}
      <Snackbar
        open={!!toastMsg}
        autoHideDuration={4000}
        onClose={() => setToastMsg(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success" variant="filled" onClose={() => setToastMsg(null)}>
          {toastMsg}
        </Alert>
      </Snackbar>
    </Stack>
  );
}
