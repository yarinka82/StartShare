import { Alert, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import FormCard from "../components/FormCard";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const { user, refresh } = useAuth();
  const [params] = useSearchParams();
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
      .then(() => {
        // tell the other tab (the one with "check your e-mail"), then close the channel
        const ch = new BroadcastChannel("auth");
        ch.postMessage("email_verified");
        ch.close();
        // this tab shares the session cookie, so a logged-in user gets the fresh state too
        void refresh();
        setState("ok");
      })
      .catch(() => setState("failed"));
  }, [token, attempt, refresh]);

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
