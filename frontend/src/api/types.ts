export type Role = "startup" | "investor";

export interface User {
  id: number;
  email: string;
  role: Role;
  email_verified: boolean;
}

/** One list value. `code` is what is stored and sent to the API; `name` is a fallback label. */
export interface Option {
  code: string;
  name: string;
}

export interface Dictionaries {
  sectors: Option[];
  stages: Option[];
  business_models: Option[];
  countries: Option[];
  growth_periods: Option[];
}

export interface Deck {
  original_name: string;
  size: number;
  status: string;
  uploaded_at: string;
}

export interface Profile {
  company_name: string;
  sector: string; // "" = not chosen yet
  stage: string;
  business_model: string;
  country: string | null;
  amount_sought: string | null;
  mrr: string | null;
  growth_percent: string | null;
  growth_period: "" | "mom" | "yoy";
  team_size: number | null;
  status: "DRAFT" | "LIVE" | "PAUSED" | "REMOVED";
  deck: Deck | null;
  is_complete: boolean;
  missing_fields: string[];
}
