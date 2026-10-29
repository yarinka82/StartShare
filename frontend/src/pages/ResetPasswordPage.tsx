import { Alert, Button, Stack } from "@mui/material";
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
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await api.resetPassword(params.get("uid") ?? "", params.get("token") ?? "", password);
      setDone(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  const pwError = err?.fields.new_password?.map((c) => errorText(t, c)).join(" ");

  return (
    <FormCard title={t("reset.title")}>
      {done ? (
        <>
          <Alert severity="success">{t("reset.done")}</Alert>
          <Button component={RouterLink} to="/login" variant="contained">
            {t("common.backToLogin")}
          </Button>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <Stack spacing={2.5}>
            {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}
            <PasswordField
              label={t("reset.newPassword")} autoComplete="new-password" required
              value={password} onChange={(e) => setPassword(e.target.value)}
              error={!!pwError} helperText={pwError ?? t("register.passwordHelper")}
            />
            <Button type="submit" variant="contained" size="large" disabled={busy || !password}>
              {t("reset.submit")}
            </Button>
          </Stack>
        </form>
      )}
    </FormCard>
  );
}
