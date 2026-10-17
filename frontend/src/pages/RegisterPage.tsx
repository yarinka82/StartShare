import {
  Alert, Button, Checkbox, FormControl, FormControlLabel, FormHelperText, FormLabel, Link,
  Radio, RadioGroup, Stack, TextField,
} from "@mui/material";
import { useState, type FormEvent, type ReactNode } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import FormCard from "../components/FormCard";
import LegalDialog, { type LegalDoc } from "../components/LegalDialog";
import PasswordField from "../components/PasswordField";

/** Opens the document in a dialog; the href keeps "open in new tab" and middle-click working. */
function LegalLink({ doc, onOpen, children }: { doc: LegalDoc; onOpen: (d: LegalDoc) => void; children?: ReactNode }) {
  return (
    <Link
      href={`/legal/${doc}`}
      onClick={(e) => {
        if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return; // let the browser handle it
        e.preventDefault();
        e.stopPropagation(); // do not toggle the checkbox
        onOpen(doc);
      }}
    >
      {children}
    </Link>
  );
}

export default function RegisterPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [role, setRole] = useState("startup");
  const [agb, setAgb] = useState(false);
  const [ds, setDs] = useState(false);
  const [legalDoc, setLegalDoc] = useState<LegalDoc | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);

  const fieldError = (name: string) => err?.fields[name]?.map((c) => errorText(t, c)).join(" ");
  const mismatch = password2 !== "" && password !== password2;
  const canSubmit = agb && ds && !!email && !!password && password === password2 && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      await api.register({ email, password, role, accept_agb: agb, accept_datenschutz: ds });
      setDone(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <FormCard title={t("register.doneTitle")}>
        <Alert severity="success">{t("register.doneText")}</Alert>
        <Button component={RouterLink} to="/login">
          {t("common.backToLogin")}
        </Button>
      </FormCard>
    );
  }

  return (
    <FormCard title={t("register.title")}>
      <form onSubmit={submit} noValidate>
        <Stack spacing={2}>
          {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}

          <FormControl error={!!fieldError("role")}>
            <FormLabel id="role-label">{t("register.iAm")}</FormLabel>
            <RadioGroup row aria-labelledby="role-label" value={role} onChange={(e) => setRole(e.target.value)}>
              <FormControlLabel value="startup" control={<Radio />} label={t("roles.startup")} />
              <FormControlLabel value="investor" control={<Radio />} label={t("roles.investor")} />
            </RadioGroup>
          </FormControl>

          <TextField
            label={t("common.email")} type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            error={!!fieldError("email")} helperText={fieldError("email")}
          />
          <PasswordField
            label={t("common.password")} autoComplete="new-password" required
            visible={showPw} onVisibleChange={setShowPw}
            value={password} onChange={(e) => setPassword(e.target.value)}
            error={!!fieldError("password")} helperText={fieldError("password") ?? t("register.passwordHelper")}
          />
          <PasswordField
            label={t("register.confirmPassword")} autoComplete="new-password" required
            visible={showPw} onVisibleChange={setShowPw}
            value={password2} onChange={(e) => setPassword2(e.target.value)}
            error={mismatch} helperText={mismatch ? t("register.passwordMismatch") : undefined}
          />

          <FormControl error={!!fieldError("accept_agb")}>
            <FormControlLabel
              control={<Checkbox checked={agb} onChange={(e) => setAgb(e.target.checked)} />}
              label={<Trans i18nKey="register.agb" components={{ link: <LegalLink doc="agb" onOpen={setLegalDoc} /> }} />}
            />
            {fieldError("accept_agb") && <FormHelperText>{fieldError("accept_agb")}</FormHelperText>}
          </FormControl>
          <FormControl error={!!fieldError("accept_datenschutz")}>
            <FormControlLabel
              control={<Checkbox checked={ds} onChange={(e) => setDs(e.target.checked)} />}
              label={<Trans i18nKey="register.datenschutz" components={{ link: <LegalLink doc="datenschutz" onOpen={setLegalDoc} /> }} />}
            />
            {fieldError("accept_datenschutz") && <FormHelperText>{fieldError("accept_datenschutz")}</FormHelperText>}
          </FormControl>

          <Button type="submit" variant="contained" size="large" disabled={!canSubmit}>
            {t("register.submit")}
          </Button>
          <Button component={RouterLink} to="/login">
            {t("register.haveAccount")}
          </Button>
        </Stack>
      </form>
      <LegalDialog doc={legalDoc} onClose={() => setLegalDoc(null)} />
    </FormCard>
  );
}
