
export type FieldName =
  | "headline"
  | "problem"
  | "solution"
  | "traction"
  | "market"
  | "team";

export const FIELD_NAMES: FieldName[] = [
  "headline",
  "problem",
  "solution",
  "traction",
  "market",
  "team",
];

export interface RiskPhrase {
  field: FieldName;
  quote: string;
  category_id: string;
  severity: "blocking" | "warning";
  start_offset?: number;
  end_offset?: number;
}

export const isBlocking = (p: RiskPhrase) => p.severity === "blocking";

export interface ApprovalBlocker {
  field: FieldName;
  code: "required" | "unconfirmed" | "blocking_risk" | "too_long";
}

export interface TeaserContent {
  status: "DRAFT" | "APPROVED";
  content: Record<FieldName, string>;
  reviewed: FieldName[];
  risk_phrases: RiskPhrase[];
  approval_blockers: ApprovalBlocker[];
}

export interface DeckDraftResponse {
  state: "QUEUED" | "PROCESSING" | "DRAFT_READY" | "FAILED";
  error_code?: string;
  draft?: {
    review?: {
      image_slides: number[];
      blanked_fields: FieldName[];
    };
  };
}