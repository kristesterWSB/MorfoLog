import { createContext, useContext } from 'react';
import type { RegisterSchema } from '../schemas/auth';

export type AppPage = 'login' | 'register' | 'dashboard' | 'profile';

export interface AuthContextType {
  isAuthenticated: boolean;
  email: string | null;
  token: string | null;
  currentPage: AppPage;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterSchema) => Promise<void>;
  logout: () => void;
  setPage: (page: AppPage) => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
