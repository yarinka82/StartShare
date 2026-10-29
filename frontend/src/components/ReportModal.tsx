import FlagIcon from "@mui/icons-material/Flag";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { errorText, parseError } from "../api/errors";

interface Props {
  open: boolean;
  onClose: () => void;
  startupPublicId: string;
}

const REPORT_REASONS = [
  { code: "fraud_scam", labelKey: "dsa.reasons.fraud_scam" },
  { code: "misleading_metrics", labelKey: "dsa.reasons.misleading_metrics" },
  { code: "ip_infringe", labelKey: "dsa.reasons.ip_infringe" },
  { code: "illegal_content", labelKey: "dsa.reasons.illegal_content" },
  { code: "other", labelKey: "dsa.reasons.other" },
];

export default function ReportModal({ open, onClose, startupPublicId }: Props) {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [reason, setReason] = useState("fraud_scam");
  const [explanation, setExplanation] = useState("");
  const [name, setName] = useState(user?.email ? user.email.split("@")[0] : "");
  const [email, setEmail] = useState(user?.email || "");
  const [goodFaith, setGoodFaith] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    setError(null);
    if (!email || !explanation || !goodFaith) {
      setError(t("dsa.requiredFields", "Будь ласка, заповніть усі обов'язкові поля."));
      return;
    }

    try {
      setBusy(true);

      await api.submitReport(startupPublicId, {
        reason_category: reason,
        explanation: explanation.trim(),
        reporter_name: name.trim(),
        reporter_email: email.trim(),
        declaration_good_faith: goodFaith,
      });

      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 2000);
    } catch (err: any) {
      // Автоматичний парсинг помилок з бекенду
      const p = parseError(err);
      setError(p.detail || errorText(t, p.detail) || "Помилка при надсиланні скарги.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1, fontWeight: 700, color: "#b91c1c" }}>
        <FlagIcon color="error" />
        {t("dsa.modalTitle", "Inhalt melden (Art. 16 DSA)")}
      </DialogTitle>

      <DialogContent dividers>
        {success ? (
          <Alert severity="success" sx={{ my: 2 }}>
            {t("dsa.successMessage", "Дякуємо! Вашу скаргу прийнято. Підтвердження надіслано на вашу пошту.")}
          </Alert>
        ) : (
          <Stack spacing={2.5}>
            <Typography variant="body2" color="text.secondary">
              {t(
                "dsa.modalIntro",
                "Відповідно до ст. 16 Digital Services Act (DSA) ви можете повідомити про незаконні, оманливі або шахрайські дані в цьому профілі."
              )}
            </Typography>

            {error && <Alert severity="error">{error}</Alert>}

            <FormControl fullWidth size="small">
              <InputLabel>{t("dsa.reasonLabel", "Категорія порушення *")}</InputLabel>
              <Select value={reason} label={t("dsa.reasonLabel", "Категорія порушення *")} onChange={(e) => setReason(e.target.value)}>
                {REPORT_REASONS.map((r) => (
                  <MenuItem key={r.code} value={r.code}>
                    {t(r.labelKey, r.code)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label={t("dsa.explanationLabel", "Обґрунтування скарги *")}
              multiline
              rows={3}
              required
              fullWidth
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder={t("dsa.explanationPlaceholder", "Опишіть, чому цей контент є неправдивим або порушує правила...")}
            />

            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2 }}>
              <TextField
                label={t("dsa.nameLabel", "Ваше ім'я")}
                size="small"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <TextField
                label={t("dsa.emailLabel", "Контактний E-mail *")}
                type="email"
                required
                size="small"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                helperText={t("dsa.emailHint", "Для отримання підтвердження за ст. 16.5 DSA")}
              />
            </Box>

            {/* Вимога DSA Art. 16.2(d): Декларація сумлінності */}
            <Box sx={{ bgcolor: "#f8fafc", p: 1.5, borderRadius: 1.5, border: "1px solid #e2e8f0" }}>
              <FormControlLabel
                control={<Checkbox checked={goodFaith} onChange={(e) => setGoodFaith(e.target.checked)} color="error" />}
                label={
                  <Typography variant="caption" sx={{ color: "#334155", display: "block", lineHeight: 1.4 }} lang="de">
                    {t(
                      "dsa.goodFaithDeclaration",
                      "Ich bestätige nach bestem Wissen und Gewissen, dass die gemachten Angaben richtig und vollständig sind (Art. 16 Abs. 2 lit. d DSA)."
                    )}
                  </Typography>
                }
              />
            </Box>
          </Stack>
        )}
      </DialogContent>

      {!success && (
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={onClose} color="inherit" disabled={busy}>
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button onClick={handleSubmit} variant="contained" color="error" disabled={busy || !goodFaith}>
            {busy ? t("common.saving", "Надсилання...") : t("dsa.submitBtn", "Надіслати скаргу (Melden)")}
          </Button>
        </DialogActions>
      )}
    </Dialog>
  );
}