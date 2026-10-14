
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function PrivacyZone() {
  const { t } = useTranslation();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleExport = () => {
    // Браузер автоматично почне завантаження файлу JSON
    window.location.href = "/api/auth/export-data/";
  };

  const handleDelete = async () => {
    setError(null);
    try {
      setBusy(true);
      const res = await fetch("/api/auth/delete-account/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.password || body.detail || "Помилка при видаленні акаунта.");
      }
      // Успішно анонімізовано -> вихід на сторінку входу
      window.location.href = "/login";
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 3, mt: 3, borderRadius: 2, borderColor: "#cbd5e1", bgcolor: "#f8fafc" }}>
      <Typography variant="h6" sx={{ fontWeight: 700, color: "#0b2142", mb: 0.5 }}>
        {t("privacy.zoneTitle", "Дані та конфіденційність (DSGVO / GDPR)")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
        {t("privacy.zoneDesc", "Керуйте своїми персональними даними відповідно до європейських стандартів Art. 17 та Art. 20 DSGVO.")}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        {/* Кнопка експорту даних (Art. 20) */}
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleExport}
          sx={{ textTransform: "none", color: "#17407a", borderColor: "#17407a" }}
        >
          {t("privacy.exportBtn", "Експортувати мої дані (JSON)")}
        </Button>

        {/* Кнопка видалення акаунта (Art. 17) */}
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteForeverIcon />}
          onClick={() => setDeleteOpen(true)}
          sx={{ textTransform: "none" }}
        >
          {t("privacy.deleteAccountBtn", "Видалити мій акаунт")}
        </Button>
      </Box>

      {/* Діалог підтвердження пароля для видалення акаунта */}
      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ color: "#b91c1c", fontWeight: 700 }}>
          {t("privacy.deleteConfirmTitle", "Остаточне видалення акаунта")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t(
              "privacy.deleteConfirmWarning",
              "Ця дія є незворотною. Ваші персональні дані будуть назавжди знеособлені, вхід заблоковано, а сесію завершено. Для підтвердження введіть ваш поточний пароль:"
            )}
          </Typography>
          <TextField
            fullWidth
            type="password"
            size="small"
            label={t("common.password", "Пароль")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={!!error}
            helperText={error}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeleteOpen(false)} color="inherit" disabled={busy}>
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button variant="contained" color="error" onClick={handleDelete} disabled={!password || busy}>
            {busy ? t("common.saving", "Видалення...") : t("privacy.confirmDeleteBtn", "Видалити назавжди")}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}