export type Role = "startup" | "investor";

export interface User {
  id: number;
  email: string;
  role: Role;
  email_verified: boolean;
}

export interface DictItem {
  id: number;
  code: string;
  name: string;
}

export interface Dictionaries {
  sectors: DictItem[];
  stages: DictItem[];
  business_models: DictItem[];
  countries: DictItem[];
  growth_periods: { code: string; name: string }[];
}

export interface Deck {
  original_name: string;
  size: number;
  status: string;
  uploaded_at: string;
}

export interface Profile {
  company_name: string;
  sector: number | null;
  stage: number | null;
  business_model: number | null;
  country: number | null;
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
