import { createContext, useContext } from 'react';

export type AppPage = 'login' | 'register' | 'dashboard';

export interface AuthContextType {
  isAuthenticated: boolean;
  email: string | null;
  token: string | null;
  currentPage: AppPage;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
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
