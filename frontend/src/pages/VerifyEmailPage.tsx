import { Alert, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import FormCard from "../components/FormCard";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const { user, refresh } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token");
  const [state, setState] = useState<"loading" | "ok" | "failed">("loading");
  const [attempt, setAttempt] = useState(0);
  const startedFor = useRef<number | null>(null); // StrictMode runs effects twice in dev

  useEffect(() => {
    if (startedFor.current === attempt) return;
    startedFor.current = attempt;
    if (!token) {
      setState("failed");
      return;
    }
    setState("loading");
    api
      .verifyEmail(token)
      .then(async () => {
        const ch = new BroadcastChannel("auth");
        ch.postMessage("email_verified");
        ch.close();
        await refresh();
        setState("ok");
      })
      .catch(() => setState("failed"));
  }, [token, attempt, refresh]);

    useEffect(() => {
      if (state !== "ok" || !user) return;
      const id = window.setTimeout(() => navigate("/", { replace: true }), 1200);
      return () => window.clearTimeout(id);
    }, [state, user, navigate]);



  return (
    <FormCard title={t("verify.title", "Підтвердження e-mail")}>
      <Stack spacing={2.5}>
        {state === "loading" && (
          <Stack direction="row" spacing={2} role="status" sx={{ alignItems: "center" }}>
            <CircularProgress size={22} />
            <Typography>{t("verify.verifying")}</Typography>
          </Stack>
        )}

        {state === "ok" && <Alert severity="success">{t("verify.success")}</Alert>}

        {state === "failed" && (
          <>
            <Alert severity="error">
              {token ? t("verify.failed") : t("verify.missingToken", "У посиланні немає коду підтвердження.")}
            </Alert>
            <Typography variant="body2" color="text.secondary">
              {t("verify.failedHint", "Посилання могло застаріти. Спробуйте увійти, і ми запропонуємо надіслати лист ще раз.")}
            </Typography>
            {token && (
              <Button variant="outlined" onClick={() => setAttempt((a) => a + 1)}>
                {t("common.tryAgain", "Повторити")}
              </Button>
            )}
          </>
        )}

        {state !== "loading" && (
          <Button component={RouterLink} to={user ? "/" : "/login"} variant="contained" size="large">
            {user ? t("verify.continue", "Продовжити") : t("common.backToLogin")}
          </Button>
        )}
      </Stack>
    </FormCard>
  );
}
