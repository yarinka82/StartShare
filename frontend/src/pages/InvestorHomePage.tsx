import {
  Alert, Box, Button, Checkbox, CircularProgress,
  FormControlLabel, InputAdornment, Paper, Snackbar, Stack,
  Skeleton, TextField, Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLegalText } from "../hooks/useLegalText";

import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import type { Dictionaries, InvestorState, Mandate, MandateInput, Option } from "../api/types";
import ChipSelect from "../components/ChipSelect";

const trimDecimal = (v: string) => v.replace(/\.00$/, "");

const emptyForm = (): MandateInput => ({
  sector_codes: [],
  stage_codes: [],
  country_codes: [],
  region_codes: [],
  business_model_codes: [],
  check_min_eur: "",
  check_max_eur: "",
});

const toForm = (m: Mandate | null): MandateInput =>
  m
    ? {
        sector_codes: m.sector_codes,
        stage_codes: m.stage_codes,
        country_codes: m.country_codes,
        region_codes: m.region_codes,
        business_model_codes: m.business_model_codes,
        check_min_eur: trimDecimal(m.check_min_eur),
        check_max_eur: trimDecimal(m.check_max_eur),
      }
    : emptyForm();

/* ---------- step 1: text C ---------- */

function StatusConfirm({ onDone }: { onDone: (s: InvestorState) => void }) {
  const { t } = useTranslation();
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const translation = t("investor.status.translation");
  const { statement, loading, error } = useLegalText("C");

  async function confirm() {
    setBusy(true);
    setErr(null);
    try {
      onDone(await api.confirmInvestorStatus());
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  const legalUnavailable = !loading && (!!error || !statement);

  return (
    <Paper variant="outlined" sx={{ p: { xs: 2.5, sm: 4 }, maxWidth: 720, mx: "auto" }}>
      <Stack spacing={2.5}>
        <Typography variant="h5" component="h1">{t("investor.status.title")}</Typography>
        <Typography color="text.secondary">{t("investor.status.intro")}</Typography>

        {err && (
          <Alert severity="error">
            {errorText(t, err.detail ?? Object.values(err.fields)[0]?.[0])}
          </Alert>
        )}

        <Box sx={{ borderLeft: "4px solid", borderColor: "primary.main", bgcolor: "action.hover", p: 2, borderRadius: 1 }}>
          {loading ? (
            <Skeleton variant="text" />
          ) : legalUnavailable ? (
            <Alert severity="error">
              {t("legal.unavailable", "Rechtstext konnte nicht geladen werden.")}
            </Alert>
          ) : (
            <Typography lang="de">{statement}</Typography>
          )}
        </Box>

        {translation && (
          <Typography variant="body2" color="text.secondary">
            {t("investor.status.translationNote")}: {translation}
          </Typography>
        )}

        <FormControlLabel
          control={
            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              disabled={legalUnavailable || loading}
            />
          }
          label={<span lang="de">{t("legal.consent.confirm")}</span>}
        />

        <Box>
          <Button
            variant="contained"
            size="large"
            disabled={!checked || busy || legalUnavailable || loading}
            onClick={confirm}
          >
            {t("investor.status.continue")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}

/* ---------- step 2: mandate ---------- */

function MandateForm({ dicts, initial }: { dicts: Dictionaries; initial: Mandate | null }) {
  const { t, i18n } = useTranslation();
  const [form, setForm] = useState<MandateInput>(toForm(initial));
  const [baseline, setBaseline] = useState<MandateInput | null>(initial ? toForm(initial) : null);
  const [createdAt, setCreatedAt] = useState<string | null>(initial?.created_at ?? null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<ParsedError | null>(null);
  const [savedMsg, setSavedMsg] = useState(false);

  const dirty = baseline === null || JSON.stringify(form) !== JSON.stringify(baseline);
  const fieldError = (name: string) => err?.fields[name]?.map((c) => errorText(t, c)).join(" ");

  const set = <K extends keyof MandateInput>(key: K, value: MandateInput[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setErr((e) => (e ? { ...e, fields: { ...e.fields, [key]: [] } } : e));
  };

  const money = (key: "check_min_eur" | "check_max_eur", raw: string) => {
    if (/^\d{0,12}[.,]?\d{0,2}$/.test(raw)) set(key, raw);
  };

  const label = (kind: "sectors" | "stages" | "countries" | "regions" | "businessModels") => (o: Option) =>
    t(`dict.${kind}.${o.code}`, { defaultValue: o.name });

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      const saved = await api.saveMandate({
        ...form,
        check_min_eur: form.check_min_eur.replace(",", "."),
        check_max_eur: form.check_max_eur.replace(",", "."),
      });
      const normalized = toForm(saved);
      setForm(normalized);
      setBaseline(normalized);
      setCreatedAt(saved.created_at);
      setSavedMsg(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  const ticketAdornment = <InputAdornment position="end">{t("common.eur")}</InputAdornment>;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>{t("investor.mandate.title")}</Typography>
        <Typography color="text.secondary">{t("investor.mandate.intro")}</Typography>
      </Box>

      {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={3}>
          <Typography variant="h6" component="h2">{t("investor.mandate.hard")}</Typography>

          {/* Секторы */}
          <ChipSelect
            required bulk label={t("investor.mandate.sectors")} options={dicts.sectors}
            value={form.sector_codes} onChange={(v) => set("sector_codes", v)} optionLabel={label("sectors")}
            error={!!fieldError("sector_codes")} helperText={fieldError("sector_codes")}
          />

          {/* Стадии */}
          <ChipSelect
            required label={t("investor.mandate.stages")} options={dicts.stages}
            value={form.stage_codes} onChange={(v) => set("stage_codes", v)} optionLabel={label("stages")}
            error={!!fieldError("stage_codes")} helperText={fieldError("stage_codes")}
          />

          {/* Страны (Новое обязательное поле) */}
          <ChipSelect
            required label={t("investor.mandate.countries", "Länder")} options={dicts.countries}
            value={form.country_codes} onChange={(v) => set("country_codes", v)} optionLabel={label("countries")}
            error={!!fieldError("country_codes")} helperText={fieldError("country_codes")}
          />

          {/* Регионы */}
          <ChipSelect
            label={t("investor.mandate.regions")} options={dicts.regions}
            value={form.region_codes} onChange={(v) => set("region_codes", v)} optionLabel={label("regions")}
            error={!!fieldError("region_codes")} helperText={fieldError("region_codes")}
          />

          {/* Чеки */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>{t("investor.mandate.ticket")} *</Typography>
            <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
              <TextField
                label={t("investor.mandate.ticketMin")} required value={form.check_min_eur}
                onChange={(e) => money("check_min_eur", e.target.value)}
                error={!!fieldError("check_min_eur")} helperText={fieldError("check_min_eur")}
                slotProps={{ htmlInput: { inputMode: "decimal" }, input: { endAdornment: ticketAdornment } }}
              />
              <TextField
                label={t("investor.mandate.ticketMax")} required value={form.check_max_eur}
                onChange={(e) => money("check_max_eur", e.target.value)}
                error={!!fieldError("check_max_eur")} helperText={fieldError("check_max_eur")}
                slotProps={{ htmlInput: { inputMode: "decimal" }, input: { endAdornment: ticketAdornment } }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary">{t("investor.mandate.ticketHint")}</Typography>
          </Box>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={3}>
          <Typography variant="h6" component="h2">{t("investor.mandate.soft")}</Typography>
          <ChipSelect
            label={t("investor.mandate.businessModels")} options={dicts.business_models}
            value={form.business_model_codes} onChange={(v) => set("business_model_codes", v)}
            optionLabel={label("businessModels")} helperText={t("investor.mandate.businessModelsHint")}
          />
        </Stack>
      </Paper>

      <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }} useFlexGap>
        <Button variant="contained" size="large" onClick={save} disabled={busy || !dirty}>
          {busy ? <CircularProgress size={22} color="inherit" /> : t("investor.mandate.save")}
        </Button>
        {createdAt && (
          <Typography variant="body2" color="text.secondary">
            {t("investor.mandate.lastSaved", {
              date: new Date(createdAt).toLocaleString(i18n.resolvedLanguage),
            })}
          </Typography>
        )}
      </Stack>

      <Snackbar open={savedMsg} autoHideDuration={3500} onClose={() => setSavedMsg(false)}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                >
        <Alert severity="success" onClose={() => setSavedMsg(false)} variant="filled">
          {t("investor.mandate.saved")}
        </Alert>
      </Snackbar>
    </Stack>
  );
}

/* ---------- page ---------- */

export default function InvestorHomePage() {
  const { t } = useTranslation();
  const [state, setState] = useState<InvestorState | null>(null);
  const [dicts, setDicts] = useState<Dictionaries | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    Promise.all([api.investorState(), api.dictionaries()])
      .then(([s, d]) => {
        setState(s);
        setDicts(d);
      })
      .catch((ex) => setLoadError(errorText(t, parseError(ex).detail)));
  }, []);

  if (loadError) return <Alert severity="error">{loadError}</Alert>;
  if (!state || !dicts) {
    return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  }
  if (!state.status_confirmed) return <StatusConfirm onDone={setState} />;
  return <MandateForm dicts={dicts} initial={state.mandate} />;
}
