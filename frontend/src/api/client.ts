import i18n from "../i18n";
import type {Deck, Dictionaries, InvestorState, LegalDocItem, Mandate, MandateInput, Profile, User} from "./types";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown) {
    super(`API error ${status}`);
    this.status = status;
    this.data = data;
  }
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

const lang = () => i18n.resolvedLanguage ?? "de";

async function ensureCsrf(): Promise<string> {
  let token = getCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf/", { credentials: "same-origin" });
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function request<T>(path: string, method: Method = "GET", body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", "Accept-Language": lang() };
  if (method !== "GET") headers["X-CSRFToken"] = await ensureCsrf();
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(0, null);
  }
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

/** Upload with progress (fetch cannot report upload progress). */
async function uploadDeck(file: File, onProgress: (percent: number) => void): Promise<Deck> {
  const token = await ensureCsrf();
  return new Promise<Deck>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/profile/deck/");
    xhr.setRequestHeader("X-CSRFToken", token);
    xhr.setRequestHeader("Accept-Language", lang());
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      const data = xhr.responseText ? safeJson(xhr.responseText) : null;
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as Deck);
      else reject(new ApiError(xhr.status, data));
    };
    xhr.onerror = () => reject(new ApiError(0, null));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export const api = {
  // auth
  me: () => request<User>("/api/auth/me/"),
  register: (data: {
    email: string;
    password: string;
    role: string;
    accept_agb: boolean;
    accept_datenschutz: boolean;
  }) => request<{ detail: string }>("/api/auth/register/", "POST", data),
  verifyEmail: (token: string) => request("/api/auth/verify-email/", "POST", { token }),
  resendVerification: (email: string) => request("/api/auth/resend-verification/", "POST", { email }),
  login: (email: string, password: string) => request<User>("/api/auth/login/", "POST", { email, password }),
  logout: () => request<void>("/api/auth/logout/", "POST"),
  forgotPassword: (email: string) => request("/api/auth/password-reset/", "POST", { email }),
  resetPassword: (uid: string, token: string, new_password: string) =>
    request("/api/auth/password-reset/confirm/", "POST", { uid, token, new_password }),
  getActiveLegalDocs: (lang = "de") =>
    request<Record<string, LegalDocItem>>(`/api/auth/legal-documents/?lang=${lang}`),

  // profile
  dictionaries: () => request<Dictionaries>("/api/dictionaries/"),
  getProfile: () => request<Profile>("/api/profile/"),
  patchProfile: (data: Record<string, unknown>) => request<Profile>("/api/profile/", "PATCH", data),
  uploadDeck,
  deleteDeck: () => request<void>("/api/profile/deck/", "DELETE"),
  deckDownloadUrl: "/api/profile/deck/download/",
  // investor
  investorState: () => request<InvestorState>("/api/investor/"),
  confirmInvestorStatus: () => request<InvestorState>("/api/investor/confirm-status/", "POST", { accept: true }),
  saveMandate: (data: MandateInput) => request<Mandate>("/api/investor/mandate/", "PUT", data),
};

