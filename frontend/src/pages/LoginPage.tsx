import React, { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LoginRequest } from '../types';
import { toast } from 'sonner';

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [formData, setFormData] = useState<LoginRequest>({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState<Partial<LoginRequest>>({});

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = (location.state as any)?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  const validateForm = (): boolean => {
    const newErrors: Partial<LoginRequest> = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await login(formData);
      toast.success('Login successful!');
    } catch (error: any) {
      toast.error(error.detail || 'Login failed');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name as keyof LoginRequest]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mb-4 animate-bounce-gentle">
            <span className="text-2xl">🛡️</span>
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 animate-slide-up">
            Welcome Back
          </h2>
          <p className="mt-2 text-sm text-gray-600 animate-slide-up-delay">
            Sign in to access your threat intelligence dashboard
          </p>
        </div>        
        <form className="mt-8 space-y-6 bg-white p-8 rounded-xl shadow-lg border border-gray-200 animate-slide-up-delay-2" onSubmit={handleSubmit}>
          <div className="space-y-5">
            <div className="group">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2 group-focus-within:text-blue-600 transition-colors">
                Email Address
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className={`input w-full transition-all duration-200 group-focus-within:scale-102 ${
                    errors.email 
                      ? 'border-red-500 bg-red-50 animate-shake' 
                      : 'focus:border-blue-500 focus:ring-blue-500'
                  }`}
                  placeholder="Enter your email address"
                  value={formData.email}
                  onChange={handleChange}
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  {formData.email && !errors.email && (
                    <span className="text-green-500 animate-fade-in">✓</span>
                  )}
                </div>
              </div>
              {errors.email && (
                <p className="mt-2 text-sm text-red-600 animate-fade-in flex items-center">
                  <span className="mr-1">⚠️</span>
                  {errors.email}
                </p>
              )}
            </div>            
            <div className="group">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2 group-focus-within:text-blue-600 transition-colors">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  className={`input w-full transition-all duration-200 group-focus-within:scale-102 ${
                    errors.password 
                      ? 'border-red-500 bg-red-50 animate-shake' 
                      : 'focus:border-blue-500 focus:ring-blue-500'
                  }`}
                  placeholder="Enter your password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  {formData.password && !errors.password && (
                    <span className="text-green-500 animate-fade-in">✓</span>
                  )}
                </div>
              </div>
              {errors.password && (
                <p className="mt-2 text-sm text-red-600 animate-fade-in flex items-center">
                  <span className="mr-1">⚠️</span>
                  {errors.password}
                </p>
              )}
            </div>
          </div>

          <div className="mt-6">
            <button
              type="submit"
              disabled={isLoading}
              className={`btn-primary w-full py-3 px-4 text-base font-medium transition-all duration-200 transform ${
                isLoading 
                  ? 'scale-95 opacity-75 cursor-not-allowed' 
                  : 'hover:scale-105 hover:shadow-lg active:scale-95'
              }`}
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"></path>
                  </svg>
                  <span className="animate-pulse">Signing you in...</span>
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  🔐 Sign In
                </span>
              )}
            </button>
          </div>

          <div className="text-center mt-6">
            <span className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-blue-600 hover:text-blue-500 transition-colors duration-200 hover:underline"
              >
                Create one now →
              </Link>
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
