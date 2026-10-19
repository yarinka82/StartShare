import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import {
  Alert, Box, Button, CircularProgress, InputAdornment, Paper, Snackbar, Stack, TextField, Typography,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import { api } from "../api/client";
import { errorText, parseError, type ParsedError } from "../api/errors";
import type { Mandate, MandateInput, Option } from "../api/types";
import ChipSelect from "../components/ChipSelect";
import { useUnsavedGuard } from "../components/UnsavedGuard";
import { FOOTER_HEIGHT } from "../components/footerConfig";
import { useInvestor } from "./InvestorProvider";
import SectionCard from "../components/SectionCard";


const trimDecimal = (v: string) => v.replace(/\.00$/, "");

const emptyForm = (): MandateInput => ({
  sector_codes: [], stage_codes: [], country_codes: [], region_codes: [], business_model_codes: [],
  check_min_eur: "", check_max_eur: "",
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

export default function MandatePage() {
  const { t, i18n } = useTranslation();
  const { state, dicts, setMandate } = useInvestor();
  const initial = state.mandate;

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
      setMandate(saved);
      setSavedMsg(true);
    } catch (ex) {
      setErr(parseError(ex));
    } finally {
      setBusy(false);
    }
  }

  const unsaved = baseline !== null && dirty;
  // first visit: an untouched empty form is not "unsaved work"
  const hasEdits = baseline === null ? JSON.stringify(form) !== JSON.stringify(emptyForm()) : dirty;
  useUnsavedGuard(hasEdits);

  const reset = () => {
    if (!baseline) return;
    setForm(baseline);
    setErr(null);
  };

  const ticketAdornment = <InputAdornment position="end">{t("common.eur")}</InputAdornment>;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 800, color: "#0b2142" }}>
          {t("investor.mandate.title")}
        </Typography>
        <Typography color="text.secondary">{t("investor.mandate.intro")}</Typography>
      </Box>

      {err?.detail && <Alert severity="error">{errorText(t, err.detail)}</Alert>}

      <SectionCard
        title={t("investor.mandate.hard")}
        hint={t("investor.mandate.hardHint", "Стартапи, що не відповідають цим критеріям, вам не показуватимуться")}
        icon={<FilterAltOutlinedIcon fontSize="small" />}
      >
        <Stack spacing={3}>
          <ChipSelect
            required bulk label={t("investor.mandate.sectors")} options={dicts.sectors}
            value={form.sector_codes} onChange={(v) => set("sector_codes", v)} optionLabel={label("sectors")}
            error={!!fieldError("sector_codes")} helperText={fieldError("sector_codes")}
          />
          <ChipSelect
            required label={t("investor.mandate.stages")} options={dicts.stages}
            value={form.stage_codes} onChange={(v) => set("stage_codes", v)} optionLabel={label("stages")}
            error={!!fieldError("stage_codes")} helperText={fieldError("stage_codes")}
          />
          <ChipSelect
            required label={t("investor.mandate.countries", "Länder")} options={dicts.countries}
            value={form.country_codes} onChange={(v) => set("country_codes", v)} optionLabel={label("countries")}
            error={!!fieldError("country_codes")} helperText={fieldError("country_codes")}
          />
          <ChipSelect
            label={t("investor.mandate.regions")} options={dicts.regions}
            value={form.region_codes} onChange={(v) => set("region_codes", v)} optionLabel={label("regions")}
            error={!!fieldError("region_codes")} helperText={fieldError("region_codes")}
          />

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
      </SectionCard>

      <SectionCard
        title={t("investor.mandate.soft")}
        hint={t("investor.mandate.softHint", "Необов’язкові побажання")}
        icon={<TuneOutlinedIcon fontSize="small" />}
      >
        <ChipSelect
          label={t("investor.mandate.businessModels")} options={dicts.business_models}
          value={form.business_model_codes} onChange={(v) => set("business_model_codes", v)}
          optionLabel={label("businessModels")} helperText={t("investor.mandate.businessModelsHint")}
        />
      </SectionCard>

      {/* sticky action bar, kept above the fixed footer */}
      <Paper
        elevation={0}
        sx={{
          position: "sticky", bottom: FOOTER_HEIGHT + 8, zIndex: 5,
          px: { xs: 2, sm: 2.5 }, py: 1.5, borderRadius: 3,
          border: "1px solid", borderColor: unsaved ? "warning.light" : "divider",
          borderLeft: "4px solid",
          borderLeftColor: unsaved ? "warning.main" : baseline ? "success.main" : "divider",
          bgcolor: "rgba(255,255,255,0.92)", backdropFilter: "blur(8px)",
          boxShadow: "0 8px 24px rgba(16,24,40,0.12)",
          display: "flex", gap: 1.5,
          flexDirection: { xs: "column", sm: "row" },
          alignItems: { xs: "stretch", sm: "center" },
        }}
      >
        {/* state: what is going on with the mandate */}
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexGrow: 1, minWidth: 0 }}>
          {unsaved ? (
            <>
              <FiberManualRecordIcon sx={{ fontSize: 12 }} color="warning" />
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {t("investor.mandate.unsaved", "Є незбережені зміни")}
              </Typography>
            </>
          ) : baseline && createdAt ? (
            <>
              <CheckCircleIcon fontSize="small" color="success" />
              <Typography variant="body2" color="text.secondary" noWrap>
                {t("investor.mandate.lastSaved", { date: new Date(createdAt).toLocaleString(i18n.resolvedLanguage) })}
              </Typography>
            </>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("investor.mandate.notSavedYet", "Мандат ще не збережено")}
            </Typography>
          )}
        </Stack>

        {/* actions: save while editing, go to the digest once everything is saved */}
        <Stack direction="row" spacing={1} sx={{ "& > *": { flex: { xs: 1, sm: "none" } } }}>
          {unsaved && (
            <Button
              color="inherit" startIcon={<RestartAltIcon />} onClick={reset} disabled={busy}
              sx={{ textTransform: "none", color: "text.secondary" }}
            >
              {t("investor.mandate.reset", "Скасувати зміни")}
            </Button>
          )}
          {dirty ? (
            <Button
              variant="contained" onClick={save} disabled={busy}
              startIcon={busy ? <CircularProgress size={18} color="inherit" /> : <SaveOutlinedIcon />}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              {t("investor.mandate.save")}
            </Button>
          ) : (
            <Button
              variant="contained" component={RouterLink} to="/investor/feed" endIcon={<ArrowForwardIcon />}
              sx={{ textTransform: "none", fontWeight: 700 }}
            >
              {t("investor.goToFeed", "Перейти до дайджесту")}
            </Button>
          )}
        </Stack>
      </Paper>

      <Snackbar
        open={savedMsg}
        autoHideDuration={3500}
        onClose={() => setSavedMsg(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        sx={{ bottom: { xs: FOOTER_HEIGHT + 8, sm: FOOTER_HEIGHT + 24 } }}
      >
        <Alert severity="success" onClose={() => setSavedMsg(false)} variant="filled">
          {t("investor.mandate.saved")}
        </Alert>
      </Snackbar>
    </Stack>
  );
}