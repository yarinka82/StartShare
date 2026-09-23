

export interface Member {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  birth_date: string | null;
  address: string;
  join_date: string;
  status: 'active' | 'inactive';
  is_founder: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface MemberFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  birth_date: string | null;
  address: string;
  join_date: string;
  status: 'active' | 'inactive';
  is_founder: boolean;
  notes: string;
}

export interface MemberFilters {
  is_founder?: boolean;
  status?: 'active' | 'inactive' | '';
  search?: string;
}

export interface MemberListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Member[];
}

