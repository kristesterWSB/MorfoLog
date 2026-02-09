import { useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import axios from 'axios';
import { AuthContext, type AppPage } from './AuthContext';

const API_URL = 'https://localhost:7219';

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return !!localStorage.getItem('token');
  });
  const [email, setEmail] = useState<string | null>(() => {
    return localStorage.getItem('email') ?? null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('token') ?? null;
  });
  const [currentPage, setCurrentPage] = useState<AppPage>(() => {
    return localStorage.getItem('token') ? 'dashboard' : 'login';
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
