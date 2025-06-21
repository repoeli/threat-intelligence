import axios, { AxiosInstance, AxiosError } from 'axios';
import { AuthResponse, LoginRequest, RegisterRequest, ThreatIntelligenceResult, AnalysisRequest, AnalysisHistory, DashboardStats, User, ApiError } from '../types';
import { toast } from 'sonner';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });    // Request interceptor to add auth token
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

    // Response interceptor for enhanced error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Clear token and redirect to login
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        
        // Show user-friendly error messages
        const apiError = this.handleError(error);
        if (!error.config?.url?.includes('/auth/')) {
          toast.error(apiError.detail || 'An error occurred');
        }
        
        return Promise.reject(apiError);
      }
    );
  }
  private handleError(error: AxiosError): ApiError {
    if (error.response) {
      const errorMessage = (error.response.data as any)?.detail || 'An error occurred';
      const status = error.response.status;
      
      // Provide more context based on status code
      let userFriendlyMessage = errorMessage;
      if (status === 400) {
        userFriendlyMessage = `Invalid request: ${errorMessage}`;
      } else if (status === 403) {
        userFriendlyMessage = 'Access denied. Please check your permissions.';
      } else if (status === 404) {
        userFriendlyMessage = 'The requested resource was not found.';
      } else if (status === 429) {
        userFriendlyMessage = 'Too many requests. Please try again later.';
      } else if (status >= 500) {
        userFriendlyMessage = 'Server error. Please try again or contact support.';
      }
      
      return {
        detail: userFriendlyMessage,
        status_code: status,
        error_code: (error.response.data as any)?.error_code,
      };
    } else if (error.request) {
      return {
        detail: 'Network error - please check your connection and try again',
        status_code: 0,
      };
    } else {
      return {
        detail: error.message || 'An unexpected error occurred',
        status_code: 0,
      };
    }
  }
  // Authentication endpoints with enhanced feedback
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/login', credentials);
    toast.success('Welcome back! Successfully logged in.');
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await this.client.post('/auth/register', userData);
    toast.success('Account created successfully! Welcome to Threat Intel.');
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    toast.success('Successfully logged out. See you next time!');
  }
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/profile');
    return response.data;
  }  // Analysis endpoints with enhanced feedback
  async analyzeIndicator(request: AnalysisRequest): Promise<ThreatIntelligenceResult> {
    const toastId = toast.loading('Analyzing indicator... This may take a few seconds.');
    try {
      const response = await this.client.post('/analyze', request);
      toast.success('Analysis completed successfully!', { id: toastId });
      return response.data;
    } catch (error) {
      toast.dismiss(toastId);
      throw error;
    }
  }
  async getAnalysisHistory(
    limit: number = 20,
    offset: number = 0,
    filters?: any
  ): Promise<AnalysisHistory> {
    const params = { limit, offset, ...filters };
    const response = await this.client.get('/analyze/history', { params });
    return response.data;
  }

  async getAnalysisById(analysisId: string): Promise<ThreatIntelligenceResult> {
    const response = await this.client.get(`/analysis/${analysisId}`);
    return response.data;
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.client.get('/analyze/stats');
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
