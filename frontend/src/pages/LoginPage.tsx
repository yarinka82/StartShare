import { Alert, Button, CircularProgress, Stack, TextField } from "@mui/material";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import { resolveLanding } from "../auth/guards";
import { useAuth } from "../auth/AuthContext";
import FormCard from "../components/FormCard";
import PasswordField from "../components/PasswordField";

const RESEND_COOLDOWN = 60; // seconds

export default function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: unknown } | null)?.from;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const [resent, setResent] = useState(false);
  const [resendBusy, setResendBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setErr(null);
    setResent(false);
    try {
      // trim: phone keyboards like to add a trailing space
      const user = await login(email.trim(), password);
      navigate(resolveLanding(user.role, from), { replace: true });
    } catch (ex) {
      const parsed = parseError(ex);
      setErr(parsed);
      if (parsed.detail !== "email_not_verified") {
        // let the user retype the password straight away
        window.setTimeout(() => passwordRef.current?.select(), 0);
      }
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    if (resendBusy || cooldown > 0) return;
    setResendBusy(true);
    try {
      await api.resendVerification(email.trim());
      setResent(true);
      setCooldown(RESEND_COOLDOWN);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setResendBusy(false);
    }
  }

  const clearFeedback = () => {
    if (err) setErr(null);
    if (resent) setResent(false);
  };

  const notVerified = err?.detail === "email_not_verified";

  return (
    <FormCard title={t("login.title")} subtitle={t("login.subtitle", "Увійдіть до свого кабінету")}>
      <form onSubmit={submit} noValidate>
        <Stack spacing={2}>
          {notVerified ? (
            <Alert
              severity={resent ? "success" : "warning"}
              action={
                <Button color="inherit" size="small" onClick={resend} disabled={resendBusy || cooldown > 0}>
                  {cooldown > 0 ? `${t("login.resend")} (${cooldown})` : t("login.resend")}
                </Button>
              }
            >
              {resent ? t("login.resent") : t("login.notVerified")}
            </Alert>
          ) : (
            err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>
          )}

          <TextField
            label={t("common.email")}
            name="email"
            type="email"
            // "username" is what password managers look for on a login form
            autoComplete="username"
            autoFocus
            required
            fullWidth
            value={email}
            onChange={(e) => { setEmail(e.target.value); clearFeedback(); }}
            slotProps={{ htmlInput: { inputMode: "email", autoCapitalize: "none", autoCorrect: "off", spellCheck: false } }}
          />

          {/* PasswordField = TextField + "eye" button to show/hide the password */}
          <PasswordField
            label={t("common.password")}
            name="password"
            autoComplete="current-password"
            required
            fullWidth
            inputRef={passwordRef}
            value={password}
            onChange={(e) => { setPassword(e.target.value); if (err && !notVerified) setErr(null); }}
          />

          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={busy || !email.trim() || !password}
            startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
            sx={{ py: 1.4, fontSize: "1rem" }}
          >
            {t("login.submit")}
          </Button>

          <Stack
            direction="row" useFlexGap
            sx={{ pt: 1, columnGap: 1, flexWrap: "wrap", justifyContent: "space-between", alignItems: "center" }}
          >
            <Button component={RouterLink} to="/forgot-password" state={{ email: email.trim() }} size="small" sx={{ textTransform: "none", color: "text.secondary" }}>
              {t("login.forgot")}
            </Button>
            <Button component={RouterLink} to="/register" size="small" sx={{ textTransform: "none", fontWeight: 600, color: "#17407a" }}>
              {t("login.noAccount")}
            </Button>
          </Stack>
        </Stack>
      </form>
    </FormCard>
  );
}