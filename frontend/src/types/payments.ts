
export type PaymentType =
  | 'membership_fee'
  | 'donation'
  | 'sponsorship'
  | 'grant'
  | 'other';

export type PaymentStatus = 'paid' | 'owed' | string;


export const PAYMENT_TYPE_LABELS: Record<string, string> = {
  membership_fee: 'Членський внесок',
  donation: 'Пожертва',
  sponsorship: 'Спонсорська підтримка',
  grant: 'Грант',
};

export const PAYMENT_STATUS_LABELS: Record<string, string> = {
  paid: 'Оплачено',
  owed: 'Заборговано',
};

export interface Payment {
  id: number;
  member: number | null;
  member_name?: string | null;
  type: PaymentType;
  type_display?: string;
  status: PaymentStatus;
  status_display?: string;
  amount: string;
  date: string; // ISO-дата, 'YYYY-MM-DD'
  source_name?: string; // джерело для donation/sponsorship/grant
  period?: string; // період для membership_fee, напр. '2026' або '2026-Q1'
  comment?: string;
  created_at?: string;
}


export interface PaymentFormData {
  member?: number | null;
  amount: string;
  date: string;
  type: PaymentType;
  source_name: string;
  period: string;
  status: PaymentStatus;
  comment?: string;
}

export interface PaymentListParams {
  member?: number;
  type?: PaymentType;
  status?: PaymentStatus;
  date_from?: string;
  date_to?: string;
  [key: string]: any;
}

export interface PaymentBreakdownItem {
  type: PaymentType;
  type_display: string;
  total: number;
  owed: number;
}

export interface PaymentPeriodItem {
  period: string; // 'YYYY-MM'
  total: number;
  owed: number;
}

export interface FinancialOverview {
  date_from: string | null;
  date_to: string | null;
  total: number;
  owed_total: number;
  breakdown: PaymentBreakdownItem[];
  by_period: PaymentPeriodItem[];
}
