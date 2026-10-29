import type { TFunction } from "i18next";

import { ApiError } from "./client";

export interface ParsedError {
  status: number;
  /** machine code or raw text for a form-level message */
  detail?: string;
  /** field name -> list of codes / raw messages */
  fields: Record<string, string[]>;
}

export function parseError(e: unknown): ParsedError {
  if (!(e instanceof ApiError)) return { status: -1, detail: "generic", fields: {} };
  if (e.status === 0) return { status: 0, detail: "network", fields: {} };
  if (e.status === 429) return { status: 429, detail: "throttled", fields: {} };

  const out: ParsedError = { status: e.status, fields: {} };
  const data = e.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      if (key === "detail" && typeof value === "string") out.detail = value;
      else if (key === "non_field_errors" && Array.isArray(value)) out.detail = String(value[0]);
      else if (Array.isArray(value)) out.fields[key] = value.map(String);
      else if (typeof value === "string") out.fields[key] = [value];
    }
  }
  if (!out.detail && Object.keys(out.fields).length === 0) out.detail = "generic";
  return out;
}

const CODE = /^[a-z][a-z0-9_]*$/;

/**
 * Backend validation messages are stable codes (e.g. "deck_too_large") and get translated here.
 * Anything else (e.g. Django's own already-localized messages) is shown as is.
 */
export function errorText(t: TFunction, code: string | undefined, params: Record<string, unknown> = {}): string {
  if (!code) return "";
  if (!CODE.test(code)) return code;
  return t(`errors.${code}`, { defaultValue: t("errors.generic"), ...params });
}
