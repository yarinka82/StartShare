import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from "@mui/material";
import {
  createContext, useContext, useEffect, useMemo, useState, type MouseEvent, type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

type GuardValue = {
  dirty: boolean;
  setDirty: (v: boolean) => void;
  /** runs `action` now, or after the user confirms leaving when there are unsaved edits */
  requestLeave: (action: () => void) => void;
};

const GuardContext = createContext<GuardValue | null>(null);

/**
 * Lives in Layout, so it covers every in-app navigation: sidebar, top bar, footer, logout.
 * Also warns when the tab is closed or reloaded.
 */
export function UnsavedGuardProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState<{ run: () => void } | null>(null);

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const value = useMemo<GuardValue>(
    () => ({
      dirty,
      setDirty,
      requestLeave: (action) => (dirty ? setPending({ run: action }) : action()),
    }),
    [dirty],
  );

  const leave = () => {
    const p = pending;
    setPending(null);
    setDirty(false);
    p?.run();
  };

  return (
    <GuardContext.Provider value={value}>
      {children}
      <Dialog open={pending !== null} onClose={() => setPending(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>{t("common.unsavedTitle", "Є незбережені зміни")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t("common.unsavedText", "Якщо піти зараз, внесені зміни буде втрачено.")}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setPending(null)} autoFocus>{t("common.stay", "Залишитись")}</Button>
          <Button onClick={leave} color="error">{t("common.leaveWithoutSaving", "Піти без збереження")}</Button>
        </DialogActions>
      </Dialog>
    </GuardContext.Provider>
  );
}

/** Pages call this with "I have unsaved edits". */
export function useUnsavedGuard(dirty: boolean) {
  const ctx = useContext(GuardContext);
  const setDirty = ctx?.setDirty;
  useEffect(() => {
    setDirty?.(dirty);
    return () => setDirty?.(false);
  }, [dirty, setDirty]);
}

/** For buttons that do something instead of linking (e.g. logout). Without a provider it just runs. */
export function useRequestLeave() {
  const ctx = useContext(GuardContext);
  return ctx?.requestLeave ?? ((action: () => void) => action());
}

/**
 * onClick handler for a router link: asks first when there are unsaved edits.
 * Ctrl/Cmd/Shift-click (new tab) and links to the current page are left alone.
 */
export function useGuardedLink() {
  const ctx = useContext(GuardContext);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  return (to: string) => (e: MouseEvent) => {
    if (!ctx?.dirty || to === pathname) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    ctx.requestLeave(() => navigate(to));
  };
}