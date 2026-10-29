
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import {MandateHistoryDto} from "../api/types";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function MandateHistoryModal({ open, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const [history, setHistory] = useState<MandateHistoryDto[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      api
        .getMandateHistory()
        .then(setHistory)
        .catch(() => setHistory([]))
        .finally(() => setLoading(false));
    }
  }, [open]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ fontWeight: 800, color: "#0b2142" }}>
        {t("investor.mandate.historyModalTitle", "Історія версій інвестиційного мандату")}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, lineHeight: 1.6 }}>
          {t(
            "investor.mandate.historyModalDesc",
            "Кожна зміна критеріїв створює нову версію. Підбори стартапів прив'язуються до тієї версії мандату, яка діяла на момент створення дайджесту."
          )}
        </Typography>

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={30} />
          </Box>
        ) : history.length === 0 ? (
          <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3 }}>
            {t("investor.mandate.noHistory", "Історія змін поки що порожня.")}
          </Typography>
        ) : (
          <Stack spacing={2}>
            {history.map((m) => (
              <Box
                key={m.version}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  border: "1px solid",
                  borderColor: m.is_current ? "#17407a" : "#e2e8f0",
                  bgcolor: m.is_current ? "#f8fafc" : "transparent",
                }}
              >
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1 }}>
                  {/* Заголовок версії та бейдж поточної */}
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                      {t("investor.mandate.versionLabel", { version: m.version, defaultValue: `Версія ${m.version}` })}
                    </Typography>
                    {m.is_current && (
                      <Chip
                        icon={<CheckCircleIcon fontSize="small" />}
                        label={t("investor.mandate.currentVersionBadge", "Діюча версія")}
                        color="primary"
                        size="small"
                        sx={{ height: 22, fontSize: "0.7rem", fontWeight: 700 }}
                      />
                    )}
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(m.created_at).toLocaleDateString(i18n.resolvedLanguage)}
                  </Typography>
                </Box>

                {/* Діапазон чека */}
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  {t("investor.mandate.ticketLabel", "Чек")}: €{Number(m.check_min_eur).toLocaleString(i18n.resolvedLanguage)} – €{Number(m.check_max_eur).toLocaleString(i18n.resolvedLanguage)}
                </Typography>

                {/* Чіпси критеріїв */}
                <Box sx={{ mt: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                  {m.sector_codes.map((s) => (
                    <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: "0.65rem" }} />
                  ))}
                  {m.stage_codes.map((st) => (
                    <Chip key={st} label={st} size="small" sx={{ fontSize: "0.65rem" }} />
                  ))}
                </Box>
              </Box>
            ))}
          </Stack>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} color="inherit">
          {t("common.close", "Закрити")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}