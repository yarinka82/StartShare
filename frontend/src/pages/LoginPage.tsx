import { Alert, Button, Stack, TextField } from "@mui/material";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import { homeFor } from "../auth/guards";
import { useAuth } from "../auth/AuthContext";
import FormCard from "../components/FormCard";
import PasswordField from "../components/PasswordField";

export default function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const [resent, setResent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setResent(false);
    try {
      const user = await login(email, password);
      navigate(homeFor(user.role), { replace: true });
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    try {
      await api.resendVerification(email);
      setResent(true);
    } catch (ex) {
      setErr(parseError(ex));
    }
  }

  const notVerified = err?.detail === "email_not_verified";

  return (
    <FormCard title={t("login.title")}>
      <form onSubmit={submit} noValidate>
        <Stack spacing={2}>
          {notVerified ? (
            <Alert
              severity="warning"
              action={
                !resent && (
                  <Button color="inherit" size="small" onClick={resend}>
                    {t("login.resend")}
                  </Button>
                )
              }
            >
              {resent ? t("login.resent") : t("login.notVerified")}
            </Alert>
          ) : (
            err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>
          )}

          <TextField
            label={t("common.email")}
            type="email"
            autoComplete="email"
            required
            fullWidth
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          {/* PasswordField = TextField + "eye" button to show/hide the password */}
          <PasswordField
            label={t("common.password")}
            autoComplete="current-password"
            required
            fullWidth
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={busy || !email || !password}
            sx={{
              bgcolor: "#17407a",
              py: 1.4,
              fontWeight: 600,
              textTransform: "none",
              fontSize: "1rem",
              "&:hover": { bgcolor: "#0b2142" },
            }}
          >
            {t("login.submit")}
          </Button>

          <Stack direction="row" sx={{ pt: 1, justifyContent: "space-between", alignItems: "center" }}>
            <Button
              component={RouterLink}
              to="/forgot-password"
              size="small"
              sx={{ textTransform: "none", color: "text.secondary" }}
            >
              {t("login.forgot")}
            </Button>
            <Button
              component={RouterLink}
              to="/register"
              size="small"
              sx={{ textTransform: "none", fontWeight: 600, color: "#17407a" }}
            >
              {t("login.noAccount")}
            </Button>
          </Stack>
        </Stack>
      </form>
    </FormCard>
  );
}
