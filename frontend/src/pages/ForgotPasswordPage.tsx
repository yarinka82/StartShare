import { Alert, Button, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useLocation } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import FormCard from "../components/FormCard";

const RESEND_COOLDOWN = 60; // seconds

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const location = useLocation();
  // the login page passes the e-mail the user has already typed
  const prefill = (location.state as { email?: string } | null)?.email ?? "";

  const [email, setEmail] = useState(prefill);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [err, setErr] = useState<ParsedError | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);

  async function send() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    try {
      await api.forgotPassword(email.trim());
      setDone(true);
      setCooldown(RESEND_COOLDOWN);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    void send();
  }

  return (
    <FormCard title={t("forgot.title")}>
      {done ? (
        <>
          <Alert severity="success">{t("forgot.done")}</Alert>
          <Typography variant="body2" color="text.secondary">
            {t("forgot.doneHint", {
              email: email.trim(),
              defaultValue: "Адреса: {{email}}. Лист може йти кілька хвилин, перевірте також папку «Спам».",
            })}
          </Typography>
          {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}
          <Stack direction="row" useFlexGap spacing={1} sx={{ flexWrap: "wrap" }}>
            <Button variant="outlined" onClick={() => void send()} disabled={busy || cooldown > 0}>
              {cooldown > 0 ? `${t("forgot.resend", "Надіслати ще раз")} (${cooldown})` : t("forgot.resend", "Надіслати ще раз")}
            </Button>
            <Button color="inherit" onClick={() => { setDone(false); setErr(null); }}>
              {t("forgot.changeEmail", "Змінити e-mail")}
            </Button>
          </Stack>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <Stack spacing={2.5}>
            <Typography color="text.secondary">{t("forgot.text")}</Typography>
            {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}
            <TextField
              label={t("common.email")} name="email" type="email" autoComplete="username" required autoFocus
              value={email}
              onChange={(e) => { setEmail(e.target.value); if (err) setErr(null); }}
              slotProps={{ htmlInput: { inputMode: "email", autoCapitalize: "none", autoCorrect: "off", spellCheck: false } }}
            />
            <Button
              type="submit" variant="contained" size="large" disabled={busy || !email.trim()}
              startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
            >
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