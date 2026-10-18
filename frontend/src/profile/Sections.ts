
import type { Meta } from "./ProfileProvider";

export const COMPANY_FIELDS = [
  "company_name", "sector", "stage", "business_model", "country",
  "amount_sought", "mrr", "growth_percent", "growth_period", "team_size",
];

export const missingCompany = (m: Meta) => m.missing_fields.filter((f) => COMPANY_FIELDS.includes(f));