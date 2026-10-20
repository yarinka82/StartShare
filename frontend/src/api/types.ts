export type Role = "startup" | "investor" | "staff";

export interface User {
  id: string;
  email: string;
  role: Role;
  is_verified?: boolean;
  preferred_language?: string;
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
  regions: Option[];
  growth_periods: Option[];
}

export interface Deck {
  id: number | null;
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

export interface Mandate {
  version: number;
  is_current: boolean;
  sector_codes: string[];
  stage_codes: string[];
  country_codes: string[];
  region_codes: string[];
  business_model_codes: string[];
  check_min_eur: string;
  check_max_eur: string;
  source: string;
  created_at: string;
}

export interface MandateInput {
  sector_codes: string[];
  stage_codes: string[];
  country_codes: string[];
  region_codes: string[];
  business_model_codes: string[];
  check_min_eur: string;
  check_max_eur: string;
}


export interface InvestorState {
  status_confirmed: boolean;
  status_confirmed_at: string | null;
  mandate: Mandate | null;
}

export interface LegalDocItem {
  code: string;
  version: number;
  title: string;
  body: string;
  language: string;
}

export interface DigestCardDto {
  id: string; // public_id знайомства (Introduction)
  card_id: number;
  position: number;
  sector: string;
  stage: string;
  region: string;
  target_amount: number;
  mrr?: number;
  team_size?: number;
  headline: string;
  problem_solution: string;
  team_summary: string;
  match_reasons: string[]; // ['sector', 'stage', 'region', 'check_size', 'business_model']
  action: "none" | "interested" | "declined";
}

export interface MandateHistoryDto {
  version: number;
  is_current: boolean;
  created_at: string;
  check_min_eur: string;
  check_max_eur: string;
  sector_codes: string[];
  stage_codes: string[];
  country_codes: string[];
  business_model_codes: string[];
}

export interface ReportPayload {
  reason_category: string;
  explanation: string;
  reporter_name: string;
  reporter_email: string;
  declaration_good_faith: boolean;
}

export interface StartupIntroDto {
  id: string; // public_id запиту знайомства
  investor_name: string;
  investor_type: string;
  message: string;
  interested_at: string;
  expires_at: string;
}

