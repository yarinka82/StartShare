
import { useContext } from 'react';
import {AuthContext} from '../context/AuthContext';
import {AuthContextValue} from "@/types/users.ts";

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

