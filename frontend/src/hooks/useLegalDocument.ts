import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export type LegalItem = { title: string; body: string };

/** URL slug -> key in /api/auth/legal-documents/ */
const CODE: Record<string, string> = {
  agb: "AGB",
  datenschutz: "DSE",
  kriterien: "F",
  impressum: "IMPRESSUM", // check: the backend must return this key, see notes
};

// one request per language for the whole session (page and dialog share it)
const cache = new Map<string, Promise<Record<string, LegalItem>>>();

function loadAll(lang: string) {
  let p = cache.get(lang);
  if (!p) {
    p = fetch(`/api/auth/legal-documents/?lang=${lang}`).then((r) =>
      r.ok ? r.json() : Promise.reject(r.status),
    );
    cache.set(lang, p);
    p.catch(() => cache.delete(lang)); // a failed request may be retried
  }
  return p;
}

/** Loads one legal document in the current interface language. Pass null to do nothing (closed dialog). */
export function useLegalDocument(doc: string | null | undefined) {
  const { i18n } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || "de";
  const [item, setItem] = useState<LegalItem | null>(null);
  const [loading, setLoading] = useState(!!doc);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    setLoading(true);
    setError(false);
    setItem(null);
    const key = CODE[doc.toLowerCase()] ?? doc.toUpperCase();
    loadAll(lang)
      .then((data) => {
        if (cancelled) return;
        const found = data[key];
        if (found) setItem(found);
        else setError(true);
      })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [doc, lang, attempt]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  return { item, loading, error, retry, lang };
}