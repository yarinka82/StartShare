
import { useEffect, useState } from "react";
import { api } from "../api/client";

export type ConsentCode = "A" | "C";

export interface LegalTextResult {
  /** Основной текст согласия (body документа из БД). */
  statement: string | null;
  /** Версия документа — для аудита, какую редакцию принял пользователь. */
  version: number | null;
  /** Заголовок документа из БД (например, "Allgemeine Geschäftsbedingungen"). */
  title: string | null;
  loading: boolean;
  error: Error | null;
}

export function useLegalText(code: ConsentCode): LegalTextResult {
  const [statement, setStatement] = useState<string | null>(null);
  const [version, setVersion] = useState<number | null>(null);
  const [title, setTitle] = useState<string | null>(null);
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
          setStatement(null);
          setVersion(null);
          setTitle(null);
          return;
        }
        setStatement(doc.body);
        setVersion(doc.version);
        setTitle(doc.title);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setStatement(null);
        setVersion(null);
        setTitle(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  return { statement, version, title, loading, error };
}