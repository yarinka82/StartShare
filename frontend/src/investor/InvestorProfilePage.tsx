import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import { Alert, Box, Button, CircularProgress, MenuItem, Snackbar, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import type { InvestorProfileInput, Option } from "../api/types";
import { useUnsavedGuard } from "../components/UnsavedGuard";
import { useInvestor } from "./InvestorProvider";

const empty: InvestorProfileInput = {
  organization_name: "", investor_type: "", country: "", contact_person_name: "", contact_email: "",
};

export default function InvestorProfilePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { dicts, profile, setProfile } = useInvestor();
  const [done, setDone] = useState(false);
  const [form, setForm] = useState<InvestorProfileInput>(profile ?? empty);
  const [baseline, setBaseline] = useState<InvestorProfileInput>(profile ?? empty);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const [saved, setSaved] = useState(false);

  const dirty = JSON.stringify(form) !== JSON.stringify(baseline);
  useUnsavedGuard(dirty && !done);
  useEffect(() => {
      if (done) navigate("/investor", { replace: true });
    }, [done, navigate]);

  const fieldError = (name: string) => err?.fields[name]?.map((c) => errorText(t, c)).join(" ");
  const set = <K extends keyof InvestorProfileInput>(key: K, value: InvestorProfileInput[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setErr((e) => (e ? { ...e, fields: { ...e.fields, [key]: [] } } : e));
  };
  const label = (kind: "investorTypes" | "countries") => (o: Option) =>
    t(`dict.${kind}.${o.code}`, { defaultValue: o.name });

  const isNew = profile === null;
  const complete = Object.values(form).every((v) => v.trim() !== "");

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      const res = await api.saveInvestorProfile(form);
      setProfile(res);
      setBaseline(res);
      setForm(res);
      setSaved(true);
      if (isNew) setDone(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 640 }}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 800, color: "#0b2142" }}>
          {t("investor.profile.title", "Профіль інвестора")}
        </Typography>
        <Typography color="text.secondary">
          {t("investor.profile.intro", "Ці дані бачитимуть стартапи, яким ви надішлете запит на інтро")}
        </Typography>
      </Box>

      {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}

      <TextField
        required label={t("investor.profile.organization", "Організація")}
        value={form.organization_name} onChange={(e) => set("organization_name", e.target.value)}
        error={!!fieldError("organization_name")} helperText={fieldError("organization_name")}
      />

      <TextField
        select required label={t("investor.profile.type", "Тип інвестора")}
        value={form.investor_type} onChange={(e) => set("investor_type", e.target.value)}
        error={!!fieldError("investor_type")} helperText={fieldError("investor_type")}
      >
        {dicts.investor_types.map((o) => (
          <MenuItem key={o.code} value={o.code}>{label("investorTypes")(o)}</MenuItem>
        ))}
      </TextField>

      <TextField
        select required label={t("investor.profile.country", "Країна")}
        value={form.country} onChange={(e) => set("country", e.target.value)}
        error={!!fieldError("country")} helperText={fieldError("country")}
      >
        {dicts.countries.map((o) => (
          <MenuItem key={o.code} value={o.code}>{label("countries")(o)}</MenuItem>
        ))}
      </TextField>

      <TextField
        required label={t("investor.profile.contactPerson", "Контактна особа")}
        value={form.contact_person_name} onChange={(e) => set("contact_person_name", e.target.value)}
        error={!!fieldError("contact_person_name")} helperText={fieldError("contact_person_name")}
      />
      <TextField
        required type="email" label={t("investor.profile.contactEmail", "Контактний e-mail")}
        value={form.contact_email} onChange={(e) => set("contact_email", e.target.value)}
        error={!!fieldError("contact_email")} helperText={fieldError("contact_email")}
      />

      <Box>
        <Button
          variant="contained" onClick={save} disabled={busy || !complete || (!isNew && !dirty)}
          startIcon={busy ? <CircularProgress size={18} color="inherit" /> : <SaveOutlinedIcon />}
          sx={{ textTransform: "none", fontWeight: 700 }}
        >
          {isNew ? t("investor.profile.saveAndContinue", "Зберегти та продовжити") : t("common.save", "Зберегти")}
        </Button>
      </Box>

      <Snackbar open={saved} autoHideDuration={3000} onClose={() => setSaved(false)}>
        <Alert severity="success" variant="filled" onClose={() => setSaved(false)}>
          {t("investor.profile.saved", "Профіль збережено")}
        </Alert>
      </Snackbar>
    </Stack>
  );
}