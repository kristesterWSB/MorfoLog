import { createContext, useContext, ReactNode, useState, useCallback } from 'react';
import axios from 'axios';

const API_URL = 'https://localhost:7219';

export type AppPage = 'login' | 'register' | 'dashboard';

interface AuthContextType {
  isAuthenticated: boolean;
  email: string | null;
  token: string | null;
  currentPage: AppPage;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setPage: (page: AppPage) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return !!localStorage.getItem('token');
  });
  const [email, setEmail] = useState<string | null>(() => {
    return localStorage.getItem('email');
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('token');
  });
  const [currentPage, setCurrentPage] = useState<AppPage>(() => {
    return !!localStorage.getItem('token') ? 'dashboard' : 'login';
  });

  const login = useCallback(async (email: string, password: string) => {
    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        email,
        password,
      });

      const { accessToken } = response.data;
      localStorage.setItem('token', accessToken);
      localStorage.setItem('email', email);

      setToken(accessToken);
      setEmail(email);
      setIsAuthenticated(true);
      setCurrentPage('dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    try {
      const response = await axios.post(`${API_URL}/api/auth/register`, {
        email,
        password,
      });

      const { accessToken } = response.data;
      localStorage.setItem('token', accessToken);
      localStorage.setItem('email', email);

      setToken(accessToken);
      setEmail(email);
      setIsAuthenticated(true);
      setCurrentPage('dashboard');
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    setToken(null);
    setEmail(null);
    setIsAuthenticated(false);
    setCurrentPage('login');
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, email, token, currentPage, login, register, logout, setPage: setCurrentPage }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
