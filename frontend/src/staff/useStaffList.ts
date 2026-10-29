import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Loads a staff list endpoint. Checks the response status (the old code put error bodies into the table)
 * and ignores stale responses (switching tabs quickly must not show the previous tab's data).
 */
export function useStaffList<T>(url: string) {
  const [rows, setRows] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const seq = useRef(0);

  const reload = useCallback(async () => {
    const id = ++seq.current;
    setLoading(true);
    setError(false);
    try {
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      if (id !== seq.current) return;
      setRows(Array.isArray(data) ? data : (data.results ?? []));
    } catch {
      if (id === seq.current) setError(true);
    } finally {
      if (id === seq.current) setLoading(false);
    }
  }, [url]);

  useEffect(() => { void reload(); }, [reload]);

  return { rows, setRows, loading, error, reload };
}