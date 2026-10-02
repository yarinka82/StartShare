import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import FormCard from "../components/FormCard";

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.forgotPassword(email);
      setDone(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <FormCard title={t("forgot.title")}>
      {done ? (
        <Alert severity="success">{t("forgot.done")}</Alert>
      ) : (
        <form onSubmit={submit} noValidate>
          <Stack spacing={2.5}>
            <Typography color="text.secondary">{t("forgot.text")}</Typography>
            {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}
            <TextField
              label={t("common.email")} type="email" autoComplete="email" required
              value={email} onChange={(e) => setEmail(e.target.value)}
            />
            <Button type="submit" variant="contained" size="large" disabled={busy || !email}>
              {t("forgot.submit")}
            </Button>
          </Stack>
        </form>
      )}
      <Button component={RouterLink} to="/login">
        {t("common.backToLogin")}
      </Button>
    </FormCard>
  );
}
