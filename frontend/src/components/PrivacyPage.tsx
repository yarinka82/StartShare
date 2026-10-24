import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import DownloadIcon from "@mui/icons-material/Download";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import {
  Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import SectionCard from "./SectionCard";
import { api } from "../api/client";
import { errorText, parseError } from "../api/errors";

type PrivacyPageProps = {
  audience: "investor" | "startup";
};

export default function PrivacyPage({ audience }: PrivacyPageProps)  {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Art. 20: the browser starts downloading the JSON file
  const handleExport = () => {
    window.location.href = "/api/auth/export-data/";
  };

  const closeDialog = () => {
    if (busy) return;
    setOpen(false);
    setPassword("");
    setError(null);
  };

  // Art. 17: account is anonymised, login is blocked
  const handleDelete = async () => {
    setError(null);
    setBusy(true);
    try {
      await api.deleteAccount(password);
      window.location.href = "/login"; // full reload also drops all in-memory state
    } catch (e) {
      const parsed = parseError(e);
      const codes = parsed.fields.password ?? (parsed.detail ? [parsed.detail] : []);
      setError(
        codes.length
          ? codes.map((c) => errorText(t, c)).join(" ")
          : t("privacy.deleteError", "Помилка при видаленні акаунта."),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <SectionCard
        title={t("privacy.exportTitle", "Експорт даних")}
        hint={t("privacy.exportHint", "Art. 20 DSGVO")}
        icon={<FileDownloadOutlinedIcon fontSize="small" />}
      >
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t("privacy.exportText", "Завантажте копію всіх своїх даних у форматі JSON.")}
        </Typography>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleExport} sx={{ textTransform: "none" }}>
          {t("privacy.exportBtn", "Експортувати мої дані (JSON)")}
        </Button>
      </SectionCard>

      {audience === "startup" && (
        <SectionCard
          title={t("privacy.pauseTitle", "Потрібно лише приховати профіль?")}
          icon={<VisibilityOffOutlinedIcon fontSize="small" />}
        >
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("privacy.pauseText", "Поставте профіль на паузу: інвестори його не бачитимуть, а всі ваші дані збережуться. Відновити показ можна в будь-який момент.")}
          </Typography>
          <Button variant="outlined" component={RouterLink} to="/profile" sx={{ textTransform: "none" }}>
            {t("privacy.pauseBtn", "Перейти до статусу профілю")}
          </Button>
        </SectionCard>
      )}

      <SectionCard
        tone="danger"
        title={t("privacy.deleteTitle", "Видалення акаунта")}
        hint={t("privacy.deleteHint", "Art. 17 DSGVO · незворотна дія")}
        icon={<DeleteForeverIcon fontSize="small" color="error" />}
      >
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {audience === "startup"
            ? t("privacy.deleteText", "Ваші персональні дані буде назавжди знеособлено, вхід заблоковано, а профіль і тизер більше не показуватимуться інвесторам. Відновити акаунт неможливо.")
            : t("privacy.deleteTextInvestor", "Ваші персональні дані буде назавжди знеособлено, вхід заблоковано, а ваш мандат більше не використовуватиметься для підбору стартапів. Відновити акаунт неможливо.")}
        </Typography>
        <Button color="error" variant="outlined" startIcon={<DeleteForeverIcon />} onClick={() => setOpen(true)} sx={{ textTransform: "none" }}>
          {t("privacy.deleteAccountBtn", "Видалити акаунт назавжди")}
        </Button>
      </SectionCard>

      <Dialog open={open} onClose={closeDialog} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ color: "error.dark", fontWeight: 700 }}>
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
            fullWidth autoFocus type="password" size="small"
            label={t("common.password", "Пароль")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && password && !busy) void handleDelete(); }}
            error={!!error}
            helperText={error}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={closeDialog} color="inherit" disabled={busy}>{t("common.cancel", "Скасувати")}</Button>
          <Button variant="contained" color="error" onClick={() => void handleDelete()} disabled={!password || busy}>
            {busy ? t("common.saving", "Видалення...") : t("privacy.confirmDeleteBtn", "Видалити назавжди")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}