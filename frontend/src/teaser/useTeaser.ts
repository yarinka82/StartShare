
import { useCallback, useEffect, useState } from "react";
import { teaserApi, type TeaserApi } from "./api";
import type { FieldName, TeaserContent } from "./types";

export function useTeaser(deckId: number, autoFetch = true, api: TeaserApi = teaserApi) {
  const [teaser, setTeaser] = useState<TeaserContent | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchTeaser = useCallback(async () => {
    try {
      setBusy(true);
      const data = await api.getTeaser(deckId);
      setTeaser(data);
      setLoadError(null);
    } catch (err: any) {
      setLoadError(err?.message || "Failed to load teaser content");
    } finally {
      setBusy(false);
    }
  }, [deckId, api]);

  useEffect(() => {
    if (autoFetch && deckId) {
      void fetchTeaser();
    }
  }, [deckId, autoFetch, fetchTeaser]);

  const saveField = async (field: FieldName, value: string): Promise<string | null> => {
    try {
      setBusy(true);
      const updated = await api.saveField(deckId, field, value);
      setTeaser(updated);
      return null;
    } catch (err: any) {
      return err?.message || "Failed to save field";
    } finally {
      setBusy(false);
    }
  };

  const confirmField = async (field: FieldName): Promise<string | null> => {
    try {
      setBusy(true);
      const updated = await api.confirmField(deckId, field);
      setTeaser(updated);
      return null;
    } catch (err: any) {
      return err?.message || "Failed to confirm field";
    } finally {
      setBusy(false);
    }
  };

  const approve = async (): Promise<string | null> => {
    try {
      setBusy(true);
      await api.approveTeaser(deckId);
      if (teaser) {
        setTeaser({ ...teaser, status: "APPROVED" });
      }
      return null;
    } catch (err: any) {
      return err?.message || "Failed to approve teaser";
    } finally {
      setBusy(false);
    }
  };

  return { teaser, loadError, busy, saveField, confirmField, approve, refetch: fetchTeaser };
}