import { Alert, Snackbar } from "@mui/material";
import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";
import { FOOTER_HEIGHT } from "../components/footerConfig";
import { api } from "../api/client";
import type { StartupIntroDto } from "../api/types";

type Toast = { severity: "success" | "error"; message: string } | null;

type IntrosContextValue = {
  intros: StartupIntroDto[];
  loading: boolean;
  error: boolean;
  busyId: string | null;
  reload: () => Promise<void>;
  respond: (id: string, action: "freigabe" | "nein") => Promise<void>;
};

const IntrosContext = createContext<IntrosContextValue | null>(null);

export function useIntros(): IntrosContextValue {
  const ctx = useContext(IntrosContext);
  if (!ctx) throw new Error("useIntros must be used inside <IntrosProvider>");
  return ctx;
}

/** Holds incoming investor requests for the whole profile area (sidebar badge, overview, requests page). */
export function IntrosProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [intros, setIntros] = useState<StartupIntroDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setIntros(await api.getStartupIntros());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  const respond = useCallback(async (id: string, action: "freigabe" | "nein") => {
    setBusyId(id);
    try {
      await api.respondToStartupIntro(id, action);
      setIntros((prev) => prev.filter((item) => item.id !== id));
      setToast({
        severity: "success",
        message: action === "freigabe"
          ? t("freigabeRequests.freigabeSuccessToast",
              "Контакти успішно відкрито! Обом сторонам надіслано e-mail з контактами та Текстом E.")
          : t("freigabeRequests.declineSuccessToast", "Запит інвестора відхилено."),
      });
    } catch (e) {
      setToast({
        severity: "error",
        message: (e as Error)?.message || t("freigabeRequests.error", "Помилка при обробці запиту."),
      });
    } finally {
      setBusyId(null);
    }
  }, [t]);

  const value = useMemo(
    () => ({ intros, loading, error, busyId, reload, respond }),
    [intros, loading, error, busyId, reload, respond],
  );

  return (
    <IntrosContext.Provider value={value}>
      {children}
      {/* lives here, not in the list, so it stays visible after the last request disappears */}
      <Snackbar
        open={!!toast}
        autoHideDuration={4000}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        sx={{ bottom: { xs: FOOTER_HEIGHT + 8, sm: FOOTER_HEIGHT + 24 } }}
      >
        <Alert severity={toast?.severity ?? "success"} variant="filled" onClose={() => setToast(null)}>
          {toast?.message}
        </Alert>
      </Snackbar>
    </IntrosContext.Provider>
  );
}