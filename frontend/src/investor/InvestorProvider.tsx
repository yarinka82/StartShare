import { Alert, Box, CircularProgress } from "@mui/material";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { errorText, parseError } from "../api/errors";
import type { Dictionaries, InvestorProfile, InvestorState, Mandate } from "../api/types";

type InvestorContextValue = {
  state: InvestorState;
  dicts: Dictionaries;
  /** null until the investor has filled in the profile; MandatePage redirects to the profile form */
  profile: InvestorProfile | null;
  setState: (s: InvestorState) => void;
  /** keeps the mandate in sync after saving, so the form does not show stale data when you come back to it */
  setMandate: (m: Mandate) => void;
  /** same for the profile */
  setProfile: (p: InvestorProfile) => void;
};

const InvestorContext = createContext<InvestorContextValue | null>(null);

export function useInvestor(): InvestorContextValue {
  const ctx = useContext(InvestorContext);
  if (!ctx) throw new Error("useInvestor must be used inside <InvestorProvider>");
  return ctx;
}

export function InvestorProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [state, setState] = useState<InvestorState | null>(null);
  const [dicts, setDicts] = useState<Dictionaries | null>(null);
  const [loadError, setLoadError] = useState("");

useEffect(() => {
    Promise.all([api.investorState(), api.dictionaries()])
      .then(([s, d]) => {
        setState(s); // s.profile comes with the state
        setDicts(d);
      })
      .catch((ex) => setLoadError(errorText(t, parseError(ex).detail)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setMandate = useCallback((m: Mandate) => {
    setState((s) => (s ? { ...s, mandate: m } : s));
  }, []);

  const setProfile = useCallback((p: InvestorProfile) => {
    setState((s) => (s ? { ...s, profile: p } : s));
  }, []);

  const value = useMemo(
    () =>
      state && dicts
        ? { state, dicts, profile: state.profile, setState, setMandate, setProfile }
        : null,
    [state, dicts, setMandate, setProfile],
  );

  if (loadError) return <Alert severity="error">{loadError}</Alert>;
  if (!value) return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  return <InvestorContext.Provider value={value}>{children}</InvestorContext.Provider>;
}