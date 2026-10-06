
import { useCallback, useEffect, useRef, useState } from "react";
import { teaserApi } from "./api";
import type { DeckDraftResponse } from "./types";

interface Options {
  fetchDraft?: (deckId: number) => Promise<DeckDraftResponse>;
  pollIntervalMs?: number;
  timeoutMs?: number;
}

export function useDeckDraft(deckId: number | null, options: Options = {}) {
  const {
    fetchDraft = teaserApi.getDraft,
    pollIntervalMs = 2000, // опитування кожні 2 секунди
    timeoutMs = 90000,     // таймаут 90 секунд
  } = options;

  const [data, setData] = useState<DeckDraftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [isPolling, setIsPolling] = useState(false);

  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<number | undefined>(undefined);

  const poll = useCallback(async () => {
    if (deckId === null) return;

    // Перевірка на таймаут
    if (Date.now() - startTimeRef.current > timeoutMs) {
      setTimedOut(true);
      setIsPolling(false);
      return;
    }

    try {
      setIsPolling(true);
      const res = await fetchDraft(deckId);
      setData(res);
      setError(null);

      // Якщо ШІ закінчив (успішно або з помилкою) — припиняємо опитування
      if (res.state === "DRAFT_READY" || res.state === "FAILED") {
        setIsPolling(false);
        return;
      }

      // Якщо ще в черзі чи обробляється — плануємо наступний запит
      timerRef.current = window.setTimeout(poll, pollIntervalMs);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch deck status");
      setIsPolling(false);
    }
  }, [deckId, fetchDraft, pollIntervalMs, timeoutMs]);

  const refetch = useCallback(() => {
    window.clearTimeout(timerRef.current);
    startTimeRef.current = Date.now();
    setTimedOut(false);
    setError(null);
    void poll();
  }, [poll]);

  useEffect(() => {
    if (deckId !== null) {
      startTimeRef.current = Date.now();
      setTimedOut(false);
      setError(null);
      void poll();
    }

    return () => {
      window.clearTimeout(timerRef.current);
    };
  }, [deckId, poll]);

  return { data, error, timedOut, refetch, isPolling };
}