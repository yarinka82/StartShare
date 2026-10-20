import { Alert, Box, CircularProgress, Snackbar } from "@mui/material";
import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { FOOTER_HEIGHT } from "../components/footerConfig";
import { api } from "../api/client";
import { errorText, parseError } from "../api/errors";
import type { Dictionaries, Profile } from "../api/types";

export type Values = {
  company_name: string; sector: string; stage: string; business_model: string; country: string;
  amount_sought: string; mrr: string; growth_percent: string; growth_period: string; team_size: string;
};
export type Name = keyof Values;
export type Meta = Pick<Profile, "status" | "is_complete" | "missing_fields" | "deck">;
export type SaveState = "idle" | "saving" | "saved" | "error";

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

const toMeta = (p: Profile): Meta => ({
  status: p.status,
  is_complete: p.is_complete,
  missing_fields: p.missing_fields,
  deck: p.deck,
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

type ProfileContextValue = {
  values: Values;
  meta: Meta;
  dicts: Dictionaries;
  saveState: SaveState;
  fieldErrors: Record<string, string>;
  change: (name: Name, raw: string) => void;
  flush: () => Promise<void>;
  refreshMeta: () => Promise<void>;
  togglePause: () => Promise<void>;
  removeProfile: () => Promise<void>;
};

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function useProfile(): ProfileContextValue {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used inside <ProfileProvider>");
  return ctx;
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Values | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [dicts, setDicts] = useState<Dictionaries | null>(null);
  const [loadError, setLoadError] = useState("");
  const [toastOpen, setToastOpen] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const valuesRef = useRef<Values | null>(null);
  valuesRef.current = values;
  const metaRef = useRef<Meta | null>(null);
  metaRef.current = meta;
  const dirty = useRef<Set<Name>>(new Set());
  const timer = useRef<number | undefined>(undefined);

  const refreshMeta = useCallback(async () => {
    try {
      setMeta(toMeta(await api.getProfile()));
    } catch { /* keep the old state */ }
  }, []);

  const togglePause = useCallback(async () => {
    const current = metaRef.current;
    if (!current) return;
    try {
      const p = await api.patchProfile({ status: current.status === "PAUSED" ? "LIVE" : "PAUSED" });
      setMeta(toMeta(p));
    } catch {
      setSaveState("error");
      setToastOpen(true);
    }
  }, []);

  const removeProfile = useCallback(async () => {
    try {
      const p = await api.patchProfile({ status: "REMOVED" });
      setMeta(toMeta(p));
    } catch {
      setSaveState("error");
      setToastOpen(true);
    }
  }, []);

  useEffect(() => {
    Promise.all([api.getProfile(), api.dictionaries()])
      .then(([p, d]) => {
        setValues(toValues(p));
        setMeta(toMeta(p));
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
      setMeta(toMeta(p));
      setSaveState("saved");
      setToastOpen(true);
    } catch (ex) {
      const parsed = parseError(ex);
      const errs: Record<string, string> = {};
      for (const [f, codes] of Object.entries(parsed.fields)) errs[f] = codes.map((c) => errorText(t, c)).join(" ");
      setFieldErrors((e) => ({ ...e, ...errs }));
      setSaveState("error");
      setToastOpen(true);
    }
  }, [t]);

  // never lose edits when the provider unmounts (leaving the whole profile area)
  useEffect(() => () => { void flush(); }, [flush]);

  const change = useCallback((name: Name, value: string) => {
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
  }, [flush]);

  const ctx = useMemo<ProfileContextValue | null>(
    () =>
      values && meta && dicts
        ? { values, meta, dicts, saveState, fieldErrors, change, flush, refreshMeta, togglePause, removeProfile }
        : null,
    [values, meta, dicts, saveState, fieldErrors, change, flush, refreshMeta, togglePause, removeProfile],
  );

  if (loadError) return <Alert severity="error">{loadError}</Alert>;
  if (!ctx) {
    return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  }

  return (
    <ProfileContext.Provider value={ctx}>
      {children}
      <Snackbar
        open={toastOpen}
        autoHideDuration={2500}
        onClose={() => setToastOpen(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        sx={{ bottom: { xs: FOOTER_HEIGHT + 8, sm: FOOTER_HEIGHT + 24 } }}
      >
        <Alert
          severity={saveState === "error" ? "error" : "success"}
          onClose={() => setToastOpen(false)}
          variant="filled"
          sx={{ boxShadow: 3 }}
        >
          {saveState === "error" ? t("profile.saveError") : t("profile.saved")}
        </Alert>
      </Snackbar>
    </ProfileContext.Provider>
  );
}