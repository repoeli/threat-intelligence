import axios, { AxiosInstance, AxiosError } from 'axios';
import { AuthResponse, LoginRequest, RegisterRequest, ThreatIntelligenceResult, AnalysisRequest, AnalysisHistory, DashboardStats, User, ApiError } from '../types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Clear token and redirect to login
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: AxiosError): ApiError {
    if (error.response) {
      return {
        detail: (error.response.data as any)?.detail || 'An error occurred',
        status_code: error.response.status,
        error_code: (error.response.data as any)?.error_code,
      };
    } else if (error.request) {
      return {
        detail: 'Network error - please check your connection',
        status_code: 0,
      };
    } else {
      return {
        detail: error.message || 'An unexpected error occurred',
        status_code: 0,
      };
    }
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/login', credentials);
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register', userData);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/me');
    return response.data;
  }
  // Analysis endpoints
  async analyzeIndicator(request: AnalysisRequest): Promise<ThreatIntelligenceResult> {
    const response = await this.client.post('/analyze', request);
    return response.data;
  }

  async getAnalysisHistory(
    page: number = 1,
    size: number = 20,
    filters?: any
  ): Promise<AnalysisHistory> {
    const params = { page, size, ...filters };
    const response = await this.client.get('/auth/history', { params });
    return response.data;
  }

  async getAnalysisById(analysisId: string): Promise<ThreatIntelligenceResult> {
    const response = await this.client.get(`/analysis/${analysisId}`);
    return response.data;
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.client.get('/dashboard/stats');
    return response.data;
  }

  // Health check
  async getHealth(): Promise<any> {
    const response = await this.client.get('/health');
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;
