import AccountBalanceOutlinedIcon from "@mui/icons-material/AccountBalanceOutlined";
import RocketLaunchOutlinedIcon from "@mui/icons-material/RocketLaunchOutlined";
import {
  Alert, Button, Checkbox, CircularProgress, FormControl, FormControlLabel, FormHelperText, FormLabel,
  Link, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography,
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
  const canSubmit = agb && ds && !!email.trim() && !!password && password === password2 && !busy;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      await api.register({ email: email.trim(), password, role, accept_agb: agb, accept_datenschutz: ds });
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
        <Typography variant="body2" color="text.secondary">
          {t("register.doneEmail", { email: email.trim(), defaultValue: "Лист надіслано на {{email}}. Перевірте також папку «Спам»." })}
        </Typography>
        <Button component={RouterLink} to="/login" variant="outlined" sx={{ textTransform: "none" }}>
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

          <FormControl error={!!fieldError("role")} fullWidth>
            <FormLabel id="role-label" sx={{ mb: 1 }}>{t("register.iAm")}</FormLabel>
            <ToggleButtonGroup
              exclusive fullWidth color="primary" value={role} aria-labelledby="role-label"
              onChange={(_, v: string | null) => { if (v) setRole(v); }}
            >
              <ToggleButton value="startup" sx={{ textTransform: "none", py: 1.2, gap: 1 }}>
                <RocketLaunchOutlinedIcon fontSize="small" /> {t("roles.startup")}
              </ToggleButton>
              <ToggleButton value="investor" sx={{ textTransform: "none", py: 1.2, gap: 1 }}>
                <AccountBalanceOutlinedIcon fontSize="small" /> {t("roles.investor")}
              </ToggleButton>
            </ToggleButtonGroup>
            {fieldError("role") && <FormHelperText>{fieldError("role")}</FormHelperText>}
          </FormControl>

          <TextField
            label={t("common.email")} name="email" type="email" autoComplete="email" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            error={!!fieldError("email")} helperText={fieldError("email")}
            slotProps={{ htmlInput: { inputMode: "email", autoCapitalize: "none", autoCorrect: "off", spellCheck: false } }}
          />
          <PasswordField
            label={t("common.password")} name="password" autoComplete="new-password" required
            visible={showPw} onVisibleChange={setShowPw}
            value={password} onChange={(e) => setPassword(e.target.value)}
            error={!!fieldError("password")} helperText={fieldError("password") ?? t("register.passwordHelper")}
          />
          <PasswordField
            label={t("register.confirmPassword")} name="password2" autoComplete="new-password" required
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

          <Button
            type="submit" variant="contained" size="large" disabled={!canSubmit}
            startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
          >
            {t("register.submit")}
          </Button>
          <Button component={RouterLink} to="/login" sx={{ textTransform: "none" }}>
            {t("register.haveAccount")}
          </Button>
        </Stack>
      </form>
      <LegalDialog doc={legalDoc} onClose={() => setLegalDoc(null)} />
    </FormCard>
  );
}