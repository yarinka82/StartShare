import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type GuardValue = { dirty: boolean; setDirty: (v: boolean) => void };

const GuardContext = createContext<GuardValue | null>(null);

/** Knows whether the page currently has unsaved edits. Warns on tab close / reload. */
export function UnsavedGuardProvider({ children }: { children: ReactNode }) {
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const value = useMemo(() => ({ dirty, setDirty }), [dirty]);
  return <GuardContext.Provider value={value}>{children}</GuardContext.Provider>;
}

/** Used by SidebarLayout to intercept in-app navigation. */
export function useUnsavedGuardState() {
  return useContext(GuardContext);
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