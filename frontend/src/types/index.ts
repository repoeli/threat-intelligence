// API Response Types
export interface ThreatAnalysisResult {
  indicator: string;
  indicator_type: 'ip' | 'domain' | 'url' | 'hash';
  threat_score: ThreatScore;
  analysis_summary: string;
  sources: AnalysisSource[];
  metadata: Record<string, any>;
  timestamp: string;
  analysis_id: string;
}

export interface ThreatScore {
  score: number;
  risk_level: RiskLevel;
  confidence: number;
  reasoning: string;
}

export interface AnalysisSource {
  name: string;
  verdict: string;
  threat_score: number;
  metadata: Record<string, any>;
}

// User Types
export interface User {
  user_id: string;
  email: string;
  subscription: SubscriptionTier;
  created_at: string;
  analysis_count: number;
}

export enum SubscriptionTier {
  FREE = 'free',
  MEDIUM = 'medium',
  PLUS = 'plus',
  ADMIN = 'admin'
}

// Authentication Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  confirm_password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Analysis Request Types
export interface AnalysisRequest {
  indicator: string;
  include_raw_data?: boolean;
}

export interface ThreatIntelligenceResult {
  indicator: string;
  indicator_type: IndicatorType;
  status: AnalysisStatus;
  threat_score: ThreatScore;
  vendor_results: VendorResult[];
  detection_ratio: string;
  reputation?: string;
  categories: string[];
  tags: string[];
  first_seen?: string;
  last_seen?: string;
  geolocation?: Record<string, any>;
  summary?: string;
  analysis_id?: string;
  timestamp?: string;
}

export enum IndicatorType {
  IP = 'ip',
  DOMAIN = 'domain', 
  URL = 'url',
  HASH = 'hash'
}

export enum AnalysisStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  ERROR = 'error'
}

export interface VendorResult {
  vendor: string;
  verdict: string;
  confidence: number;
  details?: Record<string, any>;
}

export enum RiskLevel {
  SAFE = 'safe',
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

// Dashboard Types
export interface DashboardStats {
  total_analyses: number;
  analyses_this_month: number;
  threats_detected: number;
  subscription_tier: SubscriptionTier;
  usage_stats: UsageStats;
}

export interface UsageStats {
  requests_used: number;
  requests_limit: number;
  reset_date: string;
}

// History Types
export interface AnalysisHistory {
  results: ThreatAnalysisResult[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface HistoryFilters {
  search?: string;
  threat_level?: 'low' | 'medium' | 'high' | 'critical';
  indicator_type?: 'ip' | 'domain' | 'url' | 'hash';
  date_from?: string;
  date_to?: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'analysis_progress' | 'analysis_complete' | 'system_status';
  data: any;
}

export interface AnalysisProgress {
  analysis_id: string;
  status: 'pending' | 'analyzing' | 'complete' | 'error';
  progress: number;
  message: string;
}

// API Error Types
export interface ApiError {
  detail: string;
  error_code?: string;
  status_code: number;
}

// Form Types
export interface FormField {
  value: string;
  error?: string;
  touched: boolean;
}
