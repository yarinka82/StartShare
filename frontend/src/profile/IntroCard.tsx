import AccessTimeIcon from "@mui/icons-material/AccessTime";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import { Box, Button, Chip, Paper, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { StartupIntroDto } from "../api/types";

export default function IntroCard({ item, busy, onRespond }: {
  item: StartupIntroDto;
  busy: boolean;
  onRespond: (id: string, action: "freigabe" | "nein") => void;
}) {
  const { t, i18n } = useTranslation();

  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 2.5, sm: 3 }, borderRadius: 3,
        borderLeft: "5px solid #166534", border: "1px solid #bbf7d0", bgcolor: "#f0fdf4",
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1, mb: 1.5 }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 800, color: "#0f172a" }}>{item.investor_name}</Typography>
          <Chip label={item.investor_type} size="small" sx={{ bgcolor: "#dcfce7", color: "#166534", fontWeight: 700, mt: 0.5 }} />
        </Box>

        {item.expires_at && (
          <Chip
            icon={<AccessTimeIcon fontSize="small" />}
            label={`${t("freigabeRequests.expiresIn", "Діє до")}: ${new Date(item.expires_at).toLocaleDateString(i18n.resolvedLanguage)}`}
            size="small" variant="outlined"
            sx={{ color: "#854d0e", borderColor: "#fde047", bgcolor: "#fef9c3" }}
          />
        )}
      </Box>

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

      {/* LEGAL TEXT D: contact details stay closed until approval */}
      <Box sx={{ bgcolor: "#ffffff", p: 1.5, borderRadius: 1.5, border: "1px solid #dcfce7", my: 2 }}>
        <Typography variant="caption" sx={{ color: "#475569", display: "block", lineHeight: 1.5 }} lang="de">
          <strong>{item.investor_name}</strong>{" "}
          {t("freigabeRequests.textD", "hat Interesse an Ihrem Profil. Ihre Kontaktdaten werden erst nach Ihrer Freigabe weitergegeben.")}
        </Typography>
      </Box>

      <Stack direction="row" spacing={2} useFlexGap sx={{ pt: 1, flexWrap: "wrap" }}>
        <Button
          variant="contained" color="success" startIcon={<CheckCircleIcon />}
          disabled={busy} onClick={() => onRespond(item.id, "freigabe")}
          sx={{ bgcolor: "#166534", textTransform: "none", fontWeight: 700, px: 3, "&:hover": { bgcolor: "#14532d" } }}
        >
          {busy ? t("common.saving", "Обробка...") : t("freigabeRequests.freigabeBtn", "✓ Freigabe (Відкрити контакти)")}
        </Button>
        <Button
          variant="outlined" color="inherit" startIcon={<CloseIcon />}
          disabled={busy} onClick={() => onRespond(item.id, "nein")}
          sx={{ textTransform: "none", color: "#64748b" }}
        >
          {t("freigabeRequests.declineBtn", "Відхилити")}
        </Button>
      </Stack>
    </Paper>
  );
}