
import type { DeckDraftResponse, FieldName, TeaserContent } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export interface TeaserApi {
  getDraft: (deckId: number) => Promise<DeckDraftResponse>;
  getTeaser: (deckId: number) => Promise<TeaserContent>;
  saveField: (deckId: number, field: FieldName, value: string) => Promise<TeaserContent>;
  confirmField: (deckId: number, field: FieldName) => Promise<TeaserContent>;
  approveTeaser: (deckId: number) => Promise<void>;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const body = await res.json();
      errorMsg = body.detail || body.message || errorMsg;
    } catch { /* игнорируем */ }
    throw new ApiError(errorMsg, res.status);
  }

  return res.json();
}

export const teaserApi: TeaserApi = {
  getDraft: (deckId: number) => request<DeckDraftResponse>(`/api/decks/${deckId}/draft/`),
  getTeaser: (deckId: number) => request<TeaserContent>(`/api/decks/${deckId}/teaser/`),
  saveField: (deckId: number, field: FieldName, value: string) =>
    request<TeaserContent>(`/api/decks/${deckId}/teaser/field/`, {
      method: "PATCH",
      body: JSON.stringify({ field, value }),
    }),
  confirmField: (deckId: number, field: FieldName) =>
    request<TeaserContent>(`/api/decks/${deckId}/teaser/confirm/`, {
      method: "POST",
      body: JSON.stringify({ field }),
    }),
  approveTeaser: (deckId: number) =>
    request<void>(`/api/decks/${deckId}/teaser/approve/`, {
      method: "POST",
    }),
};

export function configureTeaserApi(customApi: Partial<TeaserApi>) {
  Object.assign(teaserApi, customApi);
}