import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, AuthResponse, LoginRequest, RegisterRequest } from '../types';
import { apiClient } from '../services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = !!user;

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        const savedUser = localStorage.getItem('user');

        if (token && savedUser) {
          // Validate token by fetching current user
          const currentUser = await apiClient.getCurrentUser();
          setUser(currentUser);
        }
      } catch (error) {
        // Token is invalid, clear storage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      setIsLoading(true);
      setError(null);      const response: any = await apiClient.login(credentials);
      
      console.log('🔐 Login response:', response);
      
      // Handle both old and new response formats
      const access_token = response.access_token || response.token?.access_token;
      const user = response.user;
      
      if (!access_token) {
        throw new Error('No access token received from server');
      }
      
      // Store token and user data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      console.log('✅ Token stored:', access_token.substring(0, 20) + '...');
      console.log('✅ User stored:', user);
      
      setUser(response.user);    } catch (error: any) {
      console.error('❌ Login error:', error);
      setError(error.detail || 'Login failed');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterRequest) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response: any = await apiClient.register(userData);
      
      // Handle both old and new response formats
      const access_token = response.access_token || response.token?.access_token;
      const user = response.user;
      
      if (!access_token) {
        throw new Error('No access token received from server');
      }
      
      // Store token and user data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
        setUser(user);
    } catch (error: any) {
      console.error('❌ Registration error:', error);
      setError(error.detail || 'Registration failed');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    try {
      apiClient.logout().catch(() => {
        // Ignore logout API errors, just clear local state
      });
    } finally {
      // Always clear local state
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      setUser(null);
      setError(null);
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    error,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
