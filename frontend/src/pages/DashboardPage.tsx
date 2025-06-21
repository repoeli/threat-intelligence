import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { apiClient } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { AnalysisRequest } from '../types';
import { StatCardSkeleton, PageLoadingSkeleton } from '../components/SkeletonLoaders';

// Progress Bar Component
const ProgressBar: React.FC<{ percentage: number; color: string }> = ({ percentage, color }) => {
  const bgClass = color === 'blue' ? 'bg-gradient-to-r from-blue-500 to-blue-600' : 'bg-gradient-to-r from-green-500 to-green-600';
  const width = Math.min(100, Math.max(0, percentage));  return (
    <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
      <div 
        // @ts-ignore
        style={{ width: `${width}%` }}
        className={`${bgClass} h-3 rounded-full transition-all duration-500 ease-out`}
      />
    </div>
  );
};

// Statistics Card Component
const StatCard: React.FC<{
  title: string;
  value: number | string;
  icon: string;
  trend?: string;
  color?: string;
}> = ({ title, value, icon, trend, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    red: 'bg-red-50 text-red-700',
    purple: 'bg-purple-50 text-purple-700',
  };
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover transition-all duration-200 hover:shadow-lg hover:scale-105 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 animate-fade-in">{value}</p>
          {trend && (
            <p className="text-sm text-gray-500 mt-1">{trend}</p>
          )}
        </div>
        <div className={`p-3 rounded-full ${colorClasses[color as keyof typeof colorClasses]} transition-transform duration-200 hover:scale-110`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
    </div>
  );
};

// Risk Level Breakdown Component
const RiskBreakdown: React.FC<{ riskData: Record<string, number> }> = ({ riskData }) => {
  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'safe':
      case 'benign': return 'bg-green-500';
      case 'low': return 'bg-yellow-500';
      case 'medium': return 'bg-orange-500';
      case 'high': return 'bg-red-500';
      case 'critical': return 'bg-red-700';
      default: return 'bg-gray-500';
    }
  };

  const total = Object.values(riskData).reduce((sum, val) => sum + val, 0);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-lg transition-all duration-200 animate-slide-up-delay">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <span className="mr-2">📊</span>
        Risk Level Distribution
      </h3>
      
      {total === 0 ? (
        <div className="text-center py-8">
          <span className="text-4xl mb-4 block">📈</span>
          <p className="text-gray-500">No analysis data available</p>
          <p className="text-sm text-gray-400 mt-1">Start analyzing indicators to see risk distribution</p>
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(riskData).map(([risk, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            return (
              <div key={risk} className="flex items-center justify-between group hover:bg-gray-50 p-2 rounded transition-colors">
                <div className="flex items-center space-x-3">
                  <div className={`w-4 h-4 rounded ${getRiskColor(risk)} transition-transform group-hover:scale-110`}></div>
                  <span className="text-sm font-medium text-gray-700 capitalize">{risk}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-medium text-gray-900">{count}</span>
                  <span className="text-xs text-gray-500 ml-1">({percentage}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// Recent Analyses Component
const RecentAnalyses: React.FC<{ analyses: any[] }> = ({ analyses }) => {
  const navigate = useNavigate();

  const getRiskBadge = (riskLevel: string) => {
    const colors = {
      safe: 'bg-green-100 text-green-800',
      benign: 'bg-green-100 text-green-800',
      low: 'bg-yellow-100 text-yellow-800',
      medium: 'bg-orange-100 text-orange-800',
      high: 'bg-red-100 text-red-800',
      critical: 'bg-red-100 text-red-900',
    };
    return colors[riskLevel?.toLowerCase() as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  // Safely filter and validate analyses
  const validAnalyses = Array.isArray(analyses) ? analyses.filter(analysis => 
    analysis && 
    analysis.indicator && 
    analysis.indicator_type && 
    analysis.risk_level &&
    analysis.analyzed_at
  ) : [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-lg transition-all duration-200 animate-slide-up-delay-2">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <span className="mr-2">📋</span>
          Recent Analyses
        </h3>
        <button
          onClick={() => navigate('/history')}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors duration-200 hover:underline"
        >
          View All →
        </button>
      </div>
      
      {validAnalyses.length === 0 ? (
        <div className="text-center py-8">
          <span className="text-4xl mb-4 block">🔍</span>
          <p className="text-gray-500">No recent analyses</p>
          <p className="text-sm text-gray-400 mt-1">Your analysis history will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {validAnalyses.slice(0, 5).map((analysis) => (            <div 
              key={analysis.id || Math.random()} 
              className="flex items-center justify-between py-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 px-2 rounded transition-colors duration-200 group animate-fade-in"
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 truncate max-w-xs group-hover:text-blue-600 transition-colors">
                  {analysis.indicator}
                </p>
                <p className="text-xs text-gray-500">
                  {(analysis.indicator_type || 'unknown').toUpperCase()} • {
                    analysis.analyzed_at 
                      ? new Date(analysis.analyzed_at).toLocaleDateString()
                      : 'Unknown date'
                  }
                </p>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-sm font-medium text-gray-700">
                  {analysis.threat_score || 0}/100
                </span>
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full transition-transform group-hover:scale-105 ${getRiskBadge(analysis.risk_level || 'unknown')}`}>
                  {(analysis.risk_level || 'unknown').toUpperCase()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Quick Analysis Component
const QuickAnalysis: React.FC = () => {
  const [indicator, setIndicator] = useState('');
  const navigate = useNavigate();

  const analysisMutation = useMutation({
    mutationFn: (data: AnalysisRequest) => apiClient.analyzeIndicator(data),
    onSuccess: () => {
      toast.success('Analysis completed! Redirecting to results...');
      navigate('/analysis');
    },
    onError: (error: any) => {
      toast.error(error.detail || 'Analysis failed. Please try again.');
    }
  });

  const handleQuickAnalysis = (e: React.FormEvent) => {
    e.preventDefault();
    if (!indicator.trim()) {
      toast.error('Please enter an indicator');
      return;
    }
    
    analysisMutation.mutate({
      indicator: indicator.trim(),
      include_raw_data: false
    });
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-lg transition-all duration-200 animate-slide-up-delay">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <span className="mr-2">⚡</span>
        Quick Analysis
      </h3>
      
      <form onSubmit={handleQuickAnalysis} className="space-y-4">
        <div className="group">
          <input
            type="text"
            placeholder="Enter IP, domain, URL, or hash..."
            value={indicator}
            onChange={(e) => setIndicator(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 group-focus-within:scale-102"
          />
        </div>
        
        <div className="flex space-x-3">
          <button
            type="submit"
            disabled={analysisMutation.isPending || !indicator.trim()}
            className={`flex-1 bg-blue-600 text-white py-3 px-4 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform ${
              analysisMutation.isPending || !indicator.trim()
                ? 'opacity-50 cursor-not-allowed scale-95'
                : 'hover:bg-blue-700 hover:scale-105 hover:shadow-lg active:scale-95'
            }`}
          >
            {analysisMutation.isPending ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"></path>
                </svg>
                Analyzing...
              </span>
            ) : (
              '🔍 Analyze Now'
            )}
          </button>
          
          <button
            type="button"
            onClick={() => navigate('/analysis')}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 hover:scale-105"
          >
            Advanced
          </button>
        </div>
      </form>
    </div>
  );
};

export default function DashboardPage() {
  const { user } = useAuth();

  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.getDashboardStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch recent analyses
  const { data: history, isLoading: historyLoading, error: historyError } = useQuery({
    queryKey: ['analysis-history', 5],
    queryFn: () => apiClient.getAnalysisHistory(5, 0),
    refetchInterval: 30000,
  });

  if (statsLoading && historyLoading) {
    return <PageLoadingSkeleton title={true} stats={true} table={false} />;
  }

  if (statsError || historyError) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 rounded-md p-4 animate-fade-in">
            <div className="flex items-center">
              <span className="text-2xl mr-3">⚠️</span>
              <div>
                <p className="text-red-700 font-medium">Error loading dashboard data</p>
                <p className="text-red-600 text-sm mt-1">Please try refreshing the page or contact support if the issue persists.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Header */}
          <div className="mb-8 animate-fade-in">
            <div className="flex items-center space-x-3 mb-4">
              <div className="h-12 w-12 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-xl">🛡️</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                <p className="text-gray-600">
                  Welcome back, <span className="font-medium text-blue-600">{user?.email}</span>! Here's your threat intelligence overview.
                </p>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            {statsLoading ? (
              <>
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
                <StatCardSkeleton />
              </>
            ) : (              <>
                <div className="animate-slide-up-delay-100">
                  <StatCard
                    title="Total Analyses"
                    value={stats?.usage_stats.total_analyses || 0}
                    icon="📊"
                    trend="All time"
                    color="blue"
                  />
                </div>
                <div className="animate-slide-up-delay-200">
                  <StatCard
                    title="This Month"
                    value={stats?.usage_stats.this_month || 0}
                    icon="📅"
                    trend="Past 30 days"
                    color="green"
                  />
                </div>
                <div className="animate-slide-up-delay-300">
                  <StatCard
                    title="This Week"
                    value={stats?.usage_stats.this_week || 0}
                    icon="📈"
                    trend="Past 7 days"
                    color="purple"
                  />
                </div>
                <div className="animate-slide-up-delay-400">
                  <StatCard
                    title="High Risk Findings"
                    value={stats?.high_risk_findings || 0}
                    icon="⚠️"
                    trend="This month"
                    color="red"
                  />
                </div>
              </>
            )}
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Quick Analysis */}
            <div className="lg:col-span-1">
              <QuickAnalysis />
            </div>

            {/* Risk Breakdown */}
            <div className="lg:col-span-1">
              <RiskBreakdown riskData={stats?.risk_breakdown || {}} />
            </div>

            {/* Usage Limits */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-lg transition-all duration-200 animate-slide-up-delay-2">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">📈</span>
                  Usage & Limits
                </h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-medium">Today ({stats?.usage_stats.today || 0})</span>
                      <span className="text-gray-500">{stats?.subscription_limits.daily_limit || 0}</span>
                    </div>                    <ProgressBar 
                      percentage={((stats?.usage_stats.today || 0) / (stats?.subscription_limits.daily_limit || 1)) * 100}
                      color="blue"
                    />
                  </div>
                  
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-medium">Monthly ({stats?.usage_stats.this_month || 0})</span>
                      <span className="text-gray-500">{stats?.subscription_limits.monthly_limit || 0}</span>
                    </div>                    <ProgressBar 
                      percentage={((stats?.usage_stats.this_month || 0) / (stats?.subscription_limits.monthly_limit || 1)) * 100}
                      color="green"
                    />
                  </div>

                  <div className="pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-600 mb-3">
                      <span className="font-medium">Subscription:</span> 
                      <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                        {stats?.subscription.toUpperCase()}
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {stats?.feature_access.raw_data && (
                        <span className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                          🔍 Raw Data
                        </span>
                      )}
                      {stats?.feature_access.batch_analysis && (
                        <span className="inline-flex px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                          📊 Batch Analysis
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Analyses */}
          <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
            <div className="lg:col-span-1">
              {historyLoading ? (
                <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                  <div className="animate-pulse">
                    <div className="h-4 bg-gray-200 rounded mb-4"></div>
                    <div className="space-y-3">
                      <div className="h-12 bg-gray-200 rounded"></div>
                      <div className="h-12 bg-gray-200 rounded"></div>
                      <div className="h-12 bg-gray-200 rounded"></div>
                    </div>
                  </div>
                </div>
              ) : historyError ? (
                <div className="bg-white rounded-lg border border-red-200 p-6 shadow-sm">
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">⚠️</span>
                    <p className="text-red-600">Error loading recent analyses</p>
                  </div>
                </div>
              ) : (
                <RecentAnalyses analyses={history?.analyses || []} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
