import { Alert, Button, CircularProgress, Stack } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import FormCard from "../components/FormCard";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const [state, setState] = useState<"loading" | "ok" | "failed">("loading");
  const started = useRef(false); // StrictMode runs effects twice in dev

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = params.get("token");
    if (!token) {
      setState("failed");
      return;
    }
    api.verifyEmail(token).then(() => setState("ok")).catch(() => setState("failed"));
  }, [params]);

  return (
    <FormCard title={t("app.name")}>
      <Stack spacing={2.5}>
        {state === "loading" && (
          <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
            <CircularProgress size={22} />
            <span>{t("verify.verifying")}</span>
          </Stack>
        )}
        {state === "ok" && <Alert severity="success">{t("verify.success")}</Alert>}
        {state === "failed" && <Alert severity="error">{t("verify.failed")}</Alert>}
        {state !== "loading" && (
          <Button component={RouterLink} to="/login" variant="contained">
            {t("common.backToLogin")}
          </Button>
        )}
      </Stack>
    </FormCard>
  );
}
