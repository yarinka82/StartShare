import { Alert, Button, CircularProgress, Stack } from "@mui/material";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import FormCard from "../components/FormCard";
import PasswordField from "../components/PasswordField";

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);

  const mismatch = password2 !== "" && password !== password2;
  const canSubmit = !!password && password === password2 && !busy;
  const pwError = err?.fields.new_password?.map((c) => errorText(t, c)).join(" ");

  const newLink = (
    <Button color="inherit" size="small" component={RouterLink} to="/forgot-password">
      {t("reset.requestNew", "Запросити нове посилання")}
    </Button>
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      await api.resetPassword(uid, token, password);
      setDone(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  // the link from the e-mail is cut off: no point in asking for a password
  if (!uid || !token) {
    return (
      <FormCard title={t("reset.title")}>
        <Alert severity="error" action={newLink}>
          {t("reset.invalidLink", "Посилання недійсне або неповне.")}
        </Alert>
      </FormCard>
    );
  }

  return (
    <FormCard title={t("reset.title")}>
      {done ? (
        <>
          <Alert severity="success">{t("reset.done")}</Alert>
          <Button component={RouterLink} to="/login" variant="contained" size="large">
            {t("common.backToLogin")}
          </Button>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <Stack spacing={2.5}>
            {/* general error (e.g. the link has expired): offer a new one */}
            {err?.detail && (
              <Alert severity="error" action={newLink}>
                {errorText(t, err.detail)}
              </Alert>
            )}
            <PasswordField
              label={t("reset.newPassword")} name="new-password" autoComplete="new-password" required autoFocus
              visible={showPw} onVisibleChange={setShowPw}
              value={password} onChange={(e) => setPassword(e.target.value)}
              error={!!pwError} helperText={pwError ?? t("register.passwordHelper")}
            />
            <PasswordField
              label={t("register.confirmPassword")} name="new-password-2" autoComplete="new-password" required
              visible={showPw} onVisibleChange={setShowPw}
              value={password2} onChange={(e) => setPassword2(e.target.value)}
              error={mismatch} helperText={mismatch ? t("register.passwordMismatch") : undefined}
            />
            <Button
              type="submit" variant="contained" size="large" disabled={!canSubmit}
              startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
            >
              {t("reset.submit")}
            </Button>
          </Stack>
        </form>
      )}
    </FormCard>
  );
}
