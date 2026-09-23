

export interface User {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  first_name?: string;
  last_name?: string;
}

export interface AuthContextValue {
  user: User | null;
  username: string | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isStaff: boolean;
  userId: number | null;
}

