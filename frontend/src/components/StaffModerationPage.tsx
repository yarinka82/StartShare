
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import ShieldIcon from "@mui/icons-material/Shield";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  const [reports, setReports] = useState<ReportDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTab, setCurrentTab] = useState<"OPEN" | "RESOLVED" | "ALL">("OPEN");

  const [selectedReport, setSelectedReport] = useState<ReportDto | null>(null);
  const [decision, setDecision] = useState<"no_action" | "profile_hidden" | "profile_removed">("no_action");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const decisionLabel = {
    no_action: t("staff.moderation.action.noAction"),
    profile_hidden: t("staff.moderation.action.hide"),
    profile_removed: t("staff.moderation.action.remove"),
  }[decision];
  
  const loadReports = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/auth/staff/reports/?status=${currentTab}`, {
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      const data = await res.json();
      setReports(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadReports();
  }, [currentTab]);

  const handleOpenDecision = (report: ReportDto, dec: typeof decision) => {
    setSelectedReport(report);
    setDecision(dec);
    setNote("");
  };

  const handleConfirmDecision = async () => {
    if (!selectedReport) return;
    try {
      setBusy(true);
      const res = await fetch(`/api/auth/staff/reports/${selectedReport.id}/decide/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ decision, decision_note: note }),
      });
      if (res.ok) {
        setSelectedReport(null);
        void loadReports();
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 900, mx: "auto", py: 4 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <ShieldIcon sx={{ fontSize: 36, color: "#b91c1c" }} />
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
            {t("staff.moderation.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("staff.subtitle")}
          </Typography>
        </Box>
      </Box>

      {/* Фільтр статусів */}
      <Tabs value={currentTab} onChange={(_, val) => setCurrentTab(val)} textColor="primary">
        <Tab value="OPEN" label={t("staff.moderation.tab.open")} sx={{ fontWeight: 700 }} />
        <Tab value="RESOLVED" label={t("staff.moderation.tab.resolved")} sx={{ fontWeight: 700 }} />
        <Tab value="ALL" label={t("staff.moderation.tab.all")} />
      </Tabs>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : reports.length === 0 ? (
        <Alert severity="success">{t("staff.moderation.empty")}</Alert>
      ) : (
        <Stack spacing={2.5}>
          {reports.map((r) => (
            <Paper key={r.id} variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1.5 }}>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                  <Chip
                    label={t("staff.moderation.reportBadge", { id: r.id })}
                    size="small"
                    sx={{ fontWeight: 700 }}
                  />
                  <Chip label={r.report_type} color="error" size="small" variant="outlined" />
                  {r.moderation_hidden && (
                    <Chip label={t("staff.moderation.hiddenBadge")} color="warning" size="small" />
                  )}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {new Date(r.created_at).toLocaleString()}
                </Typography>
              </Box>

              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: "#0f172a" }}>
                {t("staff.moderation.startupId", {
                  id: r.startup_public_id,
                  sector: r.startup_sector,
                  stage: r.startup_stage,
                })}
              </Typography>

              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                {t("staff.moderation.reporter", { email: r.reporter_email })}
              </Typography>

              <Box sx={{ bgcolor: "#f8fafc", p: 1.5, borderRadius: 1.5, borderLeft: "3px solid #dc2626", my: 1.5 }}>
                <Typography variant="body2" sx={{ fontStyle: "italic", color: "#334155" }}>
                  «{r.description}»
                </Typography>
              </Box>

              {r.status === "OPEN" ? (
                <Stack direction="row" spacing={1.5} sx={{ mt: 2 }}>
                  <Button
                    variant="outlined"
                    color="inherit"
                    size="small"
                    startIcon={<CheckCircleIcon />}
                    onClick={() => handleOpenDecision(r, "no_action")}
                  >
                    {t("staff.moderation.action.noAction")}
                  </Button>
                  <Button
                    variant="outlined"
                    color="warning"
                    size="small"
                    startIcon={<VisibilityOffIcon />}
                    onClick={() => handleOpenDecision(r, "profile_hidden")}
                  >
                    {t("staff.moderation.action.hide")}
                  </Button>
                  <Button
                    variant="contained"
                    color="error"
                    size="small"
                    startIcon={<DeleteForeverIcon />}
                    onClick={() => handleOpenDecision(r, "profile_removed")}
                  >
                    {t("staff.moderation.action.remove")}
                  </Button>
                </Stack>
              ) : (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {t("staff.moderation.decisionLabel")}: <strong>{r.decision}</strong>
                </Typography>
              )}
            </Paper>
          ))}
        </Stack>
      )}

      {/* Діалог підтвердження рішення модератора */}
      <Dialog open={!!selectedReport} onClose={() => setSelectedReport(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>{t("staff.moderation.dialog.title")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {t("staff.moderation.dialog.intro", { decision: decisionLabel, id: selectedReport?.id })}
          </Typography>
          <TextField
            fullWidth
            label={t("staff.moderation.dialog.noteLabel")}
            multiline
            rows={3}
            size="small"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSelectedReport(null)} color="inherit">
            {t("common.cancel")}
          </Button>
          <Button variant="contained" color="primary" onClick={handleConfirmDecision} disabled={busy}>
            {t("staff.moderation.dialog.confirm")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}