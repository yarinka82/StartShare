import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Paper, Stack, Tab, Tabs, TextField, Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStaffList } from "./useStaffList";

type Decision = "no_action" | "profile_hidden" | "profile_removed";
type StatusTab = "OPEN" | "RESOLVED" | "ALL";

interface ReportDto {
  id: number;
  startup_public_id: string;
  startup_sector: string;
  startup_stage: string;
  startup_status: string;
  moderation_hidden: boolean;
  reporter_email: string;
  report_type: string;
  description: string;
  status: "OPEN" | "IN_REVIEW" | "RESOLVED";
  decision?: string;
  created_at: string;
}

export default function StaffModerationPage() {
  const { t, i18n } = useTranslation();
  const [tab, setTab] = useState<StatusTab>("OPEN");
  const { rows: reports, loading, error, reload } = useStaffList<ReportDto>(`/api/auth/staff/reports/?status=${tab}`);

  const [selected, setSelected] = useState<ReportDto | null>(null);
  const [decision, setDecision] = useState<Decision>("no_action");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const decisionLabel = (d: string | undefined) =>
    ({
      no_action: t("staff.moderation.action.noAction"),
      profile_hidden: t("staff.moderation.action.hide"),
      profile_removed: t("staff.moderation.action.remove"),
    } as Record<string, string>)[d ?? ""] ?? d ?? "—";

  // hiding or removing a profile affects the owner, so a reason is required (it is also what the DSA expects)
  const noteRequired = decision !== "no_action";

  const openDecision = (report: ReportDto, d: Decision) => {
    setSelected(report);
    setDecision(d);
    setNote("");
    setDialogError(null);
  };

  const closeDialog = () => {
    if (!busy) setSelected(null);
  };

  const confirmDecision = async () => {
    if (!selected || busy) return;
    setBusy(true);
    setDialogError(null);
    try {
      const res = await fetch(`/api/auth/staff/reports/${selected.id}/decide/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ decision, decision_note: note.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || t("staff.moderation.decideError", "Не вдалося зберегти рішення. Спробуйте ще раз."));
      }
      setSelected(null);
      void reload();
    } catch (e) {
      setDialogError((e as Error).message); // the dialog stays open, the note is not lost
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ borderRadius: 3 }}>
        <Tabs value={tab} onChange={(_, v: StatusTab) => setTab(v)} textColor="primary">
          <Tab value="OPEN" label={t("staff.moderation.tab.open")} />
          <Tab value="RESOLVED" label={t("staff.moderation.tab.resolved")} />
          <Tab value="ALL" label={t("staff.moderation.tab.all")} />
        </Tabs>
      </Paper>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
      ) : error ? (
        <Alert
          severity="error"
          action={<Button color="inherit" size="small" onClick={() => void reload()}>{t("common.tryAgain", "Повторити")}</Button>}
        >
          {t("staff.loadError", "Не вдалося завантажити дані.")}
        </Alert>
      ) : reports.length === 0 ? (
        <Alert severity="success">{t("staff.moderation.empty")}</Alert>
      ) : (
        <Stack spacing={2.5}>
          {reports.map((r) => (
            <Paper
              key={r.id} elevation={0}
              sx={{
                p: { xs: 2, sm: 3 }, borderRadius: 3, border: "1px solid", borderColor: "divider",
                boxShadow: "0 1px 2px rgba(16,24,40,0.04), 0 4px 12px rgba(16,24,40,0.04)",
              }}
            >
              <Box sx={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 1, mb: 1.5 }}>
                <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap" }}>
                  <Chip label={t("staff.moderation.reportBadge", { id: r.id })} size="small" sx={{ fontWeight: 700 }} />
                  <Chip label={t(`staff.moderation.type.${r.report_type}`, { defaultValue: r.report_type })} color="error" size="small" variant="outlined" />
                  {r.moderation_hidden && <Chip label={t("staff.moderation.hiddenBadge")} color="warning" size="small" />}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {new Date(r.created_at).toLocaleString(i18n.resolvedLanguage)}
                </Typography>
              </Box>

              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#0f172a" }}>
                {t("staff.moderation.startupId", { id: r.startup_public_id, sector: r.startup_sector, stage: r.startup_stage })}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                {t("staff.moderation.reporter", { email: r.reporter_email })}
              </Typography>

              <Box sx={{ bgcolor: "#f8fafc", p: 1.5, borderRadius: 1.5, borderLeft: "3px solid #dc2626", my: 1.5 }}>
                <Typography variant="body2" sx={{ fontStyle: "italic", color: "#334155", whiteSpace: "pre-wrap" }}>
                  «{r.description}»
                </Typography>
              </Box>

              {r.status !== "RESOLVED" ? (
                <Stack direction="row" spacing={1.5} useFlexGap sx={{ mt: 2, flexWrap: "wrap" }}>
                  <Button variant="outlined" color="inherit" size="small" startIcon={<CheckCircleIcon />} onClick={() => openDecision(r, "no_action")}>
                    {t("staff.moderation.action.noAction")}
                  </Button>
                  <Button variant="outlined" color="warning" size="small" startIcon={<VisibilityOffIcon />} onClick={() => openDecision(r, "profile_hidden")}>
                    {t("staff.moderation.action.hide")}
                  </Button>
                  <Button variant="contained" color="error" size="small" startIcon={<DeleteForeverIcon />} onClick={() => openDecision(r, "profile_removed")}>
                    {t("staff.moderation.action.remove")}
                  </Button>
                </Stack>
              ) : (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {t("staff.moderation.decisionLabel")}: <strong>{decisionLabel(r.decision)}</strong>
                </Typography>
              )}
            </Paper>
          ))}
        </Stack>
      )}

      <Dialog open={!!selected} onClose={closeDialog} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>{t("staff.moderation.dialog.title")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography variant="body2">
              {t("staff.moderation.dialog.intro", { decision: decisionLabel(decision), id: selected?.id })}
            </Typography>
            {decision === "profile_removed" && (
              <Alert severity="warning">
                {t("staff.moderation.dialog.removeWarning", "Профіль буде знято з платформи.")}
              </Alert>
            )}
            {dialogError && <Alert severity="error">{dialogError}</Alert>}
            <TextField
              label={t("staff.moderation.dialog.noteLabel")}
              multiline rows={3} size="small" value={note} required={noteRequired}
              onChange={(e) => setNote(e.target.value)}
              helperText={noteRequired ? t("staff.moderation.dialog.noteRequired", "Вкажіть причину рішення.") : undefined}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={closeDialog} color="inherit" disabled={busy}>{t("common.cancel")}</Button>
          <Button
            variant="contained" color={decision === "profile_removed" ? "error" : "primary"}
            onClick={confirmDecision} disabled={busy || (noteRequired && !note.trim())}
            startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
          >
            {t("staff.moderation.dialog.confirm")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}