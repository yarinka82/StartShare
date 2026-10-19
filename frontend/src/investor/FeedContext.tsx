import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { DigestCardDto } from "../api/types";

type FeedContextValue = {
  /** cards that still wait for an answer */
  cards: DigestCardDto[];
  loading: boolean;
  loadError: boolean;
  reload: () => Promise<void>;
  removeCard: (cardId: number) => void;
};

const FeedContext = createContext<FeedContextValue | null>(null);

export function useFeed(): FeedContextValue {
  const ctx = useContext(FeedContext);
  if (!ctx) throw new Error("useFeed must be used inside <FeedProvider>");
  return ctx;
}

/** Shared between the feed page and the sidebar badge. Mounted only after the investor status is confirmed. */
export function FeedProvider({ children }: { children: ReactNode }) {
  const [cards, setCards] = useState<DigestCardDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const data = await api.getInvestorFeed();
      setCards(
        data.filter((c) => !c.action || c.action === "none" || c.action.toUpperCase() === "SUGGESTED"),
      );
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  const removeCard = useCallback((cardId: number) => {
    setCards((prev) => prev.filter((c) => c.card_id !== cardId));
  }, []);

  const value = useMemo(
    () => ({ cards, loading, loadError, reload, removeCard }),
    [cards, loading, loadError, reload, removeCard],
  );
  return <FeedContext.Provider value={value}>{children}</FeedContext.Provider>;
}