
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



// Функція для отримання CSRF-токена з cookies
function getCsrfToken(): string {
  const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[2]) : "";
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const csrfToken = getCsrfToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}), // <-- Передаємо CSRF-токен
    ...(options.headers as Record<string, string>),
  };

  const res = await fetch(url, {
    credentials: "same-origin", // <-- Обов'язково передаємо сесійні куки
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorMsg = `HTTP Error ${res.status}`;
    try {
      const body = await res.json();
      errorMsg = body.detail || body.message || errorMsg;
    } catch { /* ігноруємо */ }
    throw new ApiError(errorMsg, res.status);
  }

  return res.json();
}

export const teaserApi: TeaserApi = {
  getDraft: (deckId: number) =>
    request<DeckDraftResponse>(`/api/decks/${deckId}/draft/`),

  getTeaser: (deckId: number) =>
    request<TeaserContent>(`/api/decks/${deckId}/teaser/`),

  saveField: (deckId: number, field: FieldName, value: string) =>
    request<TeaserContent>(`/api/decks/${deckId}/teaser/`, {
      method: "PATCH",
      body: JSON.stringify({
        fields: {
          [field]: value,
        },
      }),
    }),

  confirmField: (deckId: number, field: FieldName) =>
    request<TeaserContent>(`/api/decks/${deckId}/teaser/review/`, {
      method: "POST",
      body: JSON.stringify({ fields: [field] }),
    }),

  approveTeaser: (deckId: number) =>
    request<void>(`/api/decks/${deckId}/teaser/approve/`, {
      method: "POST",
      body: JSON.stringify({ declaration_a: true }),
    }),
};