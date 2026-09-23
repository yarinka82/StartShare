
import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { apiFetch } from '@/api/client';
import { AuthContextValue, User } from "@/types/users.ts";

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Сессия живёт в cookie, а не в localStorage —
    // всегда пытаемся восстановить пользователя с бэкенда
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await apiFetch('/api/auth/me/');
      if (!response.ok) {
        throw new Error('Failed to fetch user');
      }
      const data = await response.json();
      setUser(data.id ? data : null);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      setUser(data);
      window.location.href = '/home';
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await apiFetch('/api/auth/logout/', { method: 'POST' });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
    }
  };

  const value: AuthContextValue = {
    user,
    username: user?.username || null,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user,
    isStaff: user?.is_staff || false,
    userId: user?.id || null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

