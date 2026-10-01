import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, ApiError } from '../lib/api';

export type UserRole = 'citizen' | 'responder' | 'dispatcher';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified?: boolean;
}

interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  // Fetch session on mount
  const fetchSession = useCallback(async () => {
    try {
      const data = await api.get<User>('/api/v1/auth/me');
      setUser(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Not logged in — expected
        setUser(null);
      } else {
        // Transient network error — don't clear user if already loaded
        console.warn('[AuthContext] session fetch error:', err);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  const login = useCallback(async (email: string, password: string) => {
    setAuthError(null);
    setIsLoading(true);
    try {
      await api.post('/api/v1/auth/login', { email, password });
      await fetchSession();
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Login failed. Please try again.';
      setAuthError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSession]);

  const register = useCallback(async (payload: RegisterPayload) => {
    setAuthError(null);
    setIsLoading(true);
    try {
      await api.post('/api/v1/auth/register', payload);
      await fetchSession();
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : 'Registration failed. Please try again.';
      setAuthError(msg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [fetchSession]);

  const logout = useCallback(async () => {
    try {
      await api.post('/api/v1/auth/logout');
    } catch {
      // Ignore logout errors — always clear local state
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user?.is_active),
        isLoading,
        authError,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
