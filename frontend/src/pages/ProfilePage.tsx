import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import { Alert, Box, Chip, CircularProgress, InputAdornment, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api/client";
import { errorText, parseError } from "../api/errors";
import type { Deck, Dictionaries, Option, Profile } from "../api/types";
import DeckUpload from "../components/DeckUpload";

type Values = {
  company_name: string; sector: string; stage: string; business_model: string; country: string;
  amount_sought: string; mrr: string; growth_percent: string; growth_period: string; team_size: string;
};
type Name = keyof Values;
type Meta = Pick<Profile, "status" | "is_complete" | "missing_fields" | "deck">;
type SaveState = "idle" | "saving" | "saved" | "error";
type DictKind = "sectors" | "stages" | "businessModels" | "countries";

const DECIMALS: Name[] = ["amount_sought", "mrr", "growth_percent"];
const DEBOUNCE_MS = 800;

const trimDecimal = (v: string | null) => (v ?? "").replace(/\.00$/, "").replace(/(\.\d*?)0+$/, "$1");

const toValues = (p: Profile): Values => ({
  company_name: p.company_name,
  sector: p.sector,
  stage: p.stage,
  business_model: p.business_model,
  country: p.country ?? "",
  amount_sought: trimDecimal(p.amount_sought),
  mrr: trimDecimal(p.mrr),
  growth_percent: trimDecimal(p.growth_percent),
  growth_period: p.growth_period,
  team_size: p.team_size?.toString() ?? "",
});

/** undefined = value is still being typed (e.g. "-"), do not send yet */
function serialize(name: Name, v: string): unknown {
  if (name === "country") return v === "" ? null : v; // FK list: null = not chosen
  if (name === "sector" || name === "stage" || name === "business_model") return v; // choices: "" = not chosen
  if (DECIMALS.includes(name)) {
    const s = v.trim().replace(",", ".");
    if (s === "") return null;
    return /^-?\d+(\.\d+)?$/.test(s) ? s : undefined;
  }
  if (name === "team_size") return v.trim() === "" ? null : Number(v);
  return v;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
      <Typography variant="h6" component="h2" gutterBottom>{title}</Typography>
      {children}
    </Paper>
  );
}

const grid = { display: "grid", gap: 2.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } } as const;

export default function ProfilePage() {
  const { t } = useTranslation();
  const [values, setValues] = useState<Values | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [dicts, setDicts] = useState<Dictionaries | null>(null);
  const [loadError, setLoadError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const valuesRef = useRef<Values | null>(null);
  valuesRef.current = values;
  const dirty = useRef<Set<Name>>(new Set());
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    Promise.all([api.getProfile(), api.dictionaries()])
      .then(([p, d]) => {
        setValues(toValues(p));
        setMeta({ status: p.status, is_complete: p.is_complete, missing_fields: p.missing_fields, deck: p.deck });
        setDicts(d);
      })
      .catch((ex) => setLoadError(errorText(t, parseError(ex).detail)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const flush = useCallback(async () => {
    window.clearTimeout(timer.current);
    const vals = valuesRef.current;
    const names = [...dirty.current];
    dirty.current.clear();
    if (!vals || names.length === 0) return;

    const payload: Record<string, unknown> = {};
    for (const n of names) {
      const v = serialize(n, vals[n]);
      if (v !== undefined) payload[n] = v;
    }
    // growth value and period are validated together by the server
    if ("growth_percent" in payload || "growth_period" in payload) {
      const pct = serialize("growth_percent", vals.growth_percent);
      if (pct === undefined) {
        delete payload.growth_percent; delete payload.growth_period;
      } else if (pct !== null && !vals.growth_period) {
        delete payload.growth_percent; delete payload.growth_period;
        setFieldErrors((e) => ({ ...e, growth_period: errorText(t, "growth_period_required") }));
      } else {
        payload.growth_percent = pct; payload.growth_period = vals.growth_period;
      }
    }
    if (Object.keys(payload).length === 0) return;

    setSaveState("saving");
    try {
      const p = await api.patchProfile(payload);
      setMeta({ status: p.status, is_complete: p.is_complete, missing_fields: p.missing_fields, deck: p.deck });
      setSaveState("saved");
    } catch (ex) {
      const parsed = parseError(ex);
      const errs: Record<string, string> = {};
      for (const [f, codes] of Object.entries(parsed.fields)) errs[f] = codes.map((c) => errorText(t, c)).join(" ");
      setFieldErrors((e) => ({ ...e, ...errs }));
      setSaveState("error");
    }
  }, [t]);

  // never lose edits when leaving the page
  useEffect(() => () => { void flush(); }, [flush]);

  function change(name: Name, raw: string) {
    let value = raw;
    if (name === "team_size" && !/^\d{0,6}$/.test(value)) return;
    if (DECIMALS.includes(name) && !/^-?\d{0,12}[.,]?\d{0,2}$/.test(value)) return;
    setValues((v) => (v ? { ...v, [name]: value } : v));
    dirty.current.add(name);
    if (name === "growth_percent") dirty.current.add("growth_period");
    setFieldErrors((e) => {
      const { [name]: _drop, ...rest } = e;
      if (name === "growth_percent" || name === "growth_period") delete rest.growth_period;
      return rest;
    });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void flush(), DEBOUNCE_MS);
  }

  const refreshMeta = useCallback(async () => {
    try {
      const p = await api.getProfile();
      setMeta({ status: p.status, is_complete: p.is_complete, missing_fields: p.missing_fields, deck: p.deck });
    } catch { /* keep the old state */ }
  }, []);

  if (loadError) return <Alert severity="error">{loadError}</Alert>;
  if (!values || !meta || !dicts) {
    return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  }

  const label = (n: string) => t(`profile.fields.${n}`);
  const optionName = (kind: DictKind, item: Option) => t(`dict.${kind}.${item.code}`, { defaultValue: item.name });

  const select = (name: Name, items: Option[], kind: DictKind, optional = false) => (
    <TextField
      select
      label={label(name) + (optional ? ` (${t("profile.optional")})` : "")}
      // a value that was removed from the approved list is shown as "not chosen"
      value={items.some((i) => i.code === values[name]) ? values[name] : ""}
      required={!optional}
      onChange={(e) => change(name, e.target.value)}
      error={!!fieldErrors[name]} helperText={fieldErrors[name]}
    >
      {optional && <MenuItem value=""><em>—</em></MenuItem>}
      {items.map((i) => (
        <MenuItem key={i.code} value={i.code}>{optionName(kind, i)}</MenuItem>
      ))}
    </TextField>
  );

  const number = (name: Name, opts: { eur?: boolean; percent?: boolean; optional?: boolean; required?: boolean } = {}) => (
    <TextField
      label={label(name) + (opts.optional ? ` (${t("profile.optional")})` : "")}
      value={values[name]} required={opts.required}
      onChange={(e) => change(name, e.target.value)}
      error={!!fieldErrors[name]} helperText={fieldErrors[name]}
      slotProps={{
        htmlInput: { inputMode: name === "team_size" ? "numeric" : "decimal" },
        input: {
          endAdornment: opts.eur ? <InputAdornment position="end">{t("common.eur")}</InputAdornment>
            : opts.percent ? <InputAdornment position="end">%</InputAdornment> : undefined,
        },
      }}
    />
  );

  const saveIndicator = {
    idle: null,
    saving: <><CircularProgress size={14} /> {t("profile.saving")}</>,
    saved: <><CheckCircleIcon fontSize="inherit" color="success" /> {t("profile.saved")}</>,
    error: <><ErrorOutlineIcon fontSize="inherit" color="error" /> {t("profile.saveError")}</>,
  }[saveState];

  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={2} useFlexGap sx={{ alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>{t("profile.title")}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ display: "flex", alignItems: "center", gap: 0.75, minHeight: 24 }}>
          {saveIndicator}
        </Typography>
        <Chip label={t(`profile.status.${meta.status}`)} />
      </Stack>
      <Typography color="text.secondary">{t("profile.intro")}</Typography>

      {meta.is_complete ? (
        <Alert severity="success">{t("profile.complete")}</Alert>
      ) : (
        <Alert severity="info">
          {t("profile.missing")} {meta.missing_fields.map((f) => label(f)).join(", ")}
        </Alert>
      )}

      <Section title={t("profile.sections.basics")}>
        <Box sx={grid}>
          <TextField
            label={label("company_name") + ` (${t("profile.optional")})`} value={values.company_name}
            onChange={(e) => change("company_name", e.target.value)} helperText={t("profile.companyHelper")}
            slotProps={{ htmlInput: { maxLength: 200 } }}
            sx={{ gridColumn: { sm: "1 / -1" } }}
          />
          {select("sector", dicts.sectors, "sectors")}
          {select("stage", dicts.stages, "stages")}
          {select("business_model", dicts.business_models, "businessModels", true)}
          {select("country", dicts.countries, "countries")}
          {number("amount_sought", { eur: true, required: true })}
          {number("team_size", { required: true })}
        </Box>
      </Section>

      <Section title={t("profile.sections.metrics")}>
        <Box sx={grid}>
          {number("mrr", { eur: true, optional: true })}
          <Box />
          {number("growth_percent", { percent: true, optional: true })}
          <TextField
            select label={label("growth_period")} value={values.growth_period}
            onChange={(e) => change("growth_period", e.target.value)}
            error={!!fieldErrors.growth_period} helperText={fieldErrors.growth_period}
          >
            <MenuItem value=""><em>—</em></MenuItem>
            {dicts.growth_periods.map((g) => (
              <MenuItem key={g.code} value={g.code}>{t(`profile.growthPeriods.${g.code}`, { defaultValue: g.name })}</MenuItem>
            ))}
          </TextField>
        </Box>
      </Section>

      <Section title={t("profile.sections.deck")}>
        <DeckUpload deck={meta.deck as Deck | null} onChanged={refreshMeta} />
      </Section>
    </Stack>
  );
}
