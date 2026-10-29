import { useEffect, useState } from "react";
import { api } from "../api/client";

export type LegalDocCode = "AGB" | "DSE" | "F" | "IMPRESSUM";

export interface LegalDocument {
  title: string;
  body: string;
  version: number;
}

export interface LegalDocumentResult {
  data: LegalDocument | null;
  loading: boolean;
  error: Error | null;
}

export function useLegalDocument(code: LegalDocCode): LegalDocumentResult {
  const [data, setData] = useState<LegalDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getActiveLegalDocs("de")
      .then((docs) => {
        if (cancelled) return;
        const doc = docs[code] ?? docs[code.toLowerCase()];
        if (!doc) {
          setData(null);
          return;
        }
        setData({ title: doc.title, body: doc.body, version: doc.version });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  return { data, loading, error };
}