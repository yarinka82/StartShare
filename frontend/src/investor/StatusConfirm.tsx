import {
  Alert, Box, Button, Checkbox, FormControlLabel, Paper, Skeleton, Stack, Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import { useLegalText } from "../hooks/useLegalText";
import { useInvestor } from "./InvestorProvider";

/* step 1: legal text C – investor status confirmation */
export default function StatusConfirm() {
  const { t } = useTranslation();
  const { setState } = useInvestor();
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const translation = t("investor.status.translation");
  const { statement, loading, error } = useLegalText("C");

  async function confirm() {
    setBusy(true);
    setErr(null);
    try {
      const s = await api.confirmInvestorStatus();
      setState({ ...s, profile: null });
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  const legalUnavailable = !loading && (!!error || !statement);

  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 2.5, sm: 4 }, maxWidth: 720, borderRadius: 3,
        border: "1px solid", borderColor: "divider",
        boxShadow: "0 1px 2px rgba(16,24,40,0.04), 0 4px 12px rgba(16,24,40,0.04)",
      }}
    >
      <Stack spacing={2.5}>
        <Typography variant="h5" component="h1">{t("investor.status.title")}</Typography>
        <Typography color="text.secondary">{t("investor.status.intro")}</Typography>

        {err && (
          <Alert severity="error">
            {errorText(t, err.detail ?? Object.values(err.fields)[0]?.[0])}
          </Alert>
        )}

        <Box sx={{ borderLeft: "4px solid", borderColor: "primary.main", bgcolor: "action.hover", p: 2, borderRadius: 1 }}>
          {loading ? (
            <Skeleton variant="text" />
          ) : legalUnavailable ? (
            <Alert severity="error">{t("legal.unavailable", "Rechtstext konnte nicht geladen werden.")}</Alert>
          ) : (
            <Typography lang="de">{statement}</Typography>
          )}
        </Box>

        {translation && (
          <Typography variant="body2" color="text.secondary">
            {t("investor.status.translationNote")}: {translation}
          </Typography>
        )}

        <FormControlLabel
          control={<Checkbox checked={checked} onChange={(e) => setChecked(e.target.checked)} disabled={legalUnavailable || loading} />}
          label={<span lang="de">{t("legal.consent.confirm")}</span>}
        />

        <Box>
          <Button variant="contained" size="large" disabled={!checked || busy || legalUnavailable || loading} onClick={confirm}>
            {t("investor.status.continue")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}