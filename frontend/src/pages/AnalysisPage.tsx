import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '../services/api';
import { AnalysisRequest, ThreatIntelligenceResult, IndicatorType } from '../types';
import { AnalysisResultSkeleton } from '../components/SkeletonLoaders';

// Utility function to detect indicator type
const detectIndicatorType = (indicator: string): IndicatorType | null => {
  const trimmed = indicator.trim();
  
  // IP address (basic regex)
  if (/^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(trimmed)) {
    return IndicatorType.IP;
  }
  
  // Domain
  if (/^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/.test(trimmed)) {
    return IndicatorType.DOMAIN;
  }
  
  // URL
  if (/^https?:\/\/.+/.test(trimmed)) {
    return IndicatorType.URL;
  }
  
  // Hash (MD5, SHA1, SHA256)
  if (/^[a-fA-F0-9]{32}$/.test(trimmed) || /^[a-fA-F0-9]{40}$/.test(trimmed) || /^[a-fA-F0-9]{64}$/.test(trimmed)) {
    return IndicatorType.HASH;
  }
  
  return null;
};

// Component for displaying threat score
const ThreatScoreCard: React.FC<{ score: any }> = ({ score }) => {
  // Handle different response formats from backend
  const threatScore = score?.score ?? 0;
  const confidence = score?.confidence ?? 0;
  const riskLevel = score?.risk_level || score?.threat_level || 'unknown';
  const reasoning = score?.reasoning || 'Analysis completed based on multiple threat intelligence sources';

  const getRiskColor = (risk: string) => {
    const riskLower = risk.toLowerCase();
    switch (riskLower) {
      case 'safe':
      case 'benign': 
      case 'clean': return 'text-green-700 bg-green-100';
      case 'low': return 'text-yellow-700 bg-yellow-100';
      case 'medium': return 'text-orange-700 bg-orange-100';
      case 'high': return 'text-red-700 bg-red-100';
      case 'critical': return 'text-purple-700 bg-purple-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Threat Assessment</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Score Circle */}
        <div className="flex flex-col items-center">
          <div className="relative w-24 h-24 mb-3">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                className="text-gray-200"
              />              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="transparent"
                strokeDasharray={`${2 * Math.PI * 40}`}
                strokeDashoffset={`${2 * Math.PI * 40 * (1 - threatScore / 100)}`}
                strokeLinecap="round"
                className={`transition-all duration-1000 ease-in-out ${threatScore > 70 ? 'text-red-500' : threatScore > 40 ? 'text-yellow-500' : 'text-green-500'}`}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-gray-900">{Math.round(threatScore)}</span>
            </div>
          </div>
          <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${getRiskColor(riskLevel)}`}>
            {riskLevel.toUpperCase()}
          </span>
        </div>

        {/* Details */}
        <div className="md:col-span-2 space-y-4">
          <div>
            <p className="text-sm text-gray-600">Confidence Level</p>
            <div className="flex items-center space-x-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">                <div 
                  className={`bg-blue-500 h-2 rounded-full transition-all duration-1000 ease-out`}
                  style={{ width: `${confidence}%` }}
                ></div>
              </div>
              <span className="text-sm text-gray-900">{confidence}%</span>
            </div>
          </div>
          
          <div>
            <p className="text-sm text-gray-600">Analysis Summary</p>
            <p className="text-sm text-gray-900 mt-1">{reasoning}</p>
          </div>

          {score?.details && (
            <div>
              <p className="text-sm text-gray-600 mb-2">Detection Details</p>              {Object.entries(score.details).map(([key, value], index) => (
                <div key={key} className={`flex justify-between items-center py-1 animate-fade-in animate-delay-${Math.min(index * 100, 500)}`}>
                  <span className="text-sm text-gray-700 capitalize">{key.replace('_', ' ')}</span>
                  <span className="text-sm font-medium text-gray-900">{String(value)}/100</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Component for displaying vendor results
const VendorResultsCard: React.FC<{ results: any[] }> = ({ results }) => {
  if (!results || results.length === 0) return null;

  const getVerdictColor = (result: string, category: string) => {
    const resultLower = result.toLowerCase();
    const categoryLower = category.toLowerCase();
    
    if (resultLower === 'clean' || categoryLower === 'harmless') {
      return 'text-green-700 bg-green-100';
    } else if (resultLower === 'malicious' || categoryLower === 'malicious') {
      return 'text-red-700 bg-red-100';
    } else if (resultLower === 'suspicious' || categoryLower === 'suspicious') {
      return 'text-orange-700 bg-orange-100';
    } else if (resultLower === 'unrated' || categoryLower === 'undetected') {
      return 'text-gray-700 bg-gray-100';
    }
    return 'text-blue-700 bg-blue-100';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Vendor Analysis</h3>
      
      <div className="space-y-3 max-h-96 overflow-y-auto">        {results.map((result, index) => (
          <div 
            key={index} 
            className={`flex justify-between items-center py-2 border-b border-gray-100 last:border-b-0 animate-fade-in animate-delay-${Math.min(index * 150, 500)}`}
          >
            <div className="flex-1">
              <p className="font-medium text-gray-900">{result.vendor}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full transition-all ${getVerdictColor(result.result, result.category)}`}>
                  {result.result}
                </span>
                {result.category && (
                  <span className="text-xs text-gray-500">
                    ({result.category})
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default function AnalysisPage() {
  const [formData, setFormData] = useState<AnalysisRequest>({
    indicator: '',
    include_raw_data: false
  });
  const [result, setResult] = useState<ThreatIntelligenceResult | null>(null);
  
  const analysisMutation = useMutation({
    mutationFn: (data: AnalysisRequest) => apiClient.analyzeIndicator(data),
    onSuccess: (data: ThreatIntelligenceResult) => {
      setResult(data);
      toast.success('Analysis completed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.detail || 'Analysis failed. Please try again.');
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.indicator.trim()) {
      toast.error('Please enter an indicator to analyze');
      return;
    }

    const detectedType = detectIndicatorType(formData.indicator);
    if (!detectedType) {
      toast.error('Unable to detect indicator type. Please check your input.');
      return;
    }    analysisMutation.mutate({
      ...formData,
      indicator_type: detectedType
    } as AnalysisRequest);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }));
  };

  const clearResults = () => {
    setResult(null);
    setFormData({ indicator: '', include_raw_data: false });
  };

  const detectedType = formData.indicator ? detectIndicatorType(formData.indicator) : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="fade-in">
            <h1 className="text-3xl font-bold text-gray-900">Threat Analysis</h1>
            <p className="mt-2 text-gray-600">Analyze indicators for potential threats and security risks</p>
          </div>
          
          {/* Analysis Form */}
          <div className="mt-8 bg-white rounded-lg border border-gray-200 p-6 shadow-sm slide-up card-hover">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Submit Indicator for Analysis</h2>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="indicator" className="block text-sm font-medium text-gray-700">
                  Indicator
                </label>
                <textarea
                  id="indicator"
                  name="indicator"
                  rows={3}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 form-field-enhanced"
                  placeholder="Enter IP address, domain, URL, or file hash..."
                  value={formData.indicator}
                  onChange={handleChange}
                  disabled={analysisMutation.isPending}
                />
                {detectedType && (
                  <p className="mt-1 text-sm text-green-600 animate-fade-in">
                    ✓ Detected as: {detectedType.toUpperCase()}
                  </p>
                )}
                {formData.indicator && !detectedType && (
                  <p className="mt-1 text-sm text-red-600 animate-fade-in">
                    ⚠ Unable to detect indicator type. Please check your input.
                  </p>
                )}
              </div>

              <div className="flex items-center animate-fade-in-delay-1">
                <input
                  id="include_raw_data"
                  name="include_raw_data"
                  type="checkbox"
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded transition-all"
                  checked={formData.include_raw_data}
                  onChange={handleChange}
                  disabled={analysisMutation.isPending}
                />
                <label htmlFor="include_raw_data" className="ml-2 block text-sm text-gray-700">
                  Include raw vendor data in response
                </label>
              </div>

              <div className="flex space-x-3 animate-fade-in-delay-2">
                <button
                  type="submit"
                  disabled={analysisMutation.isPending || !formData.indicator.trim()}
                  className="bg-blue-600 text-white py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                >
                  {analysisMutation.isPending ? (
                    <span className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Analyzing...
                    </span>
                  ) : (
                    'Analyze Indicator'
                  )}
                </button>
                
                {result && (
                  <button
                    type="button"
                    onClick={clearResults}
                    className="bg-gray-200 text-gray-700 py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 btn-enhanced animate-scale-in"
                  >
                    Clear Results
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Loading Skeleton */}
          {analysisMutation.isPending && (
            <div className="mt-8 animate-fade-in">
              <AnalysisResultSkeleton />
            </div>
          )}

          {/* Analysis Results */}
          {result && (
            <div className="mt-8 space-y-6 animate-slide-up">
              <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Analysis Results</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div className="animate-fade-in-delay-1">
                    <p className="text-sm text-gray-600">Analyzed Indicator</p>
                    <p className="font-mono text-lg text-gray-900 break-all">{result.indicator}</p>
                  </div>
                  <div className="animate-fade-in-delay-2">
                    <p className="text-sm text-gray-600">Indicator Type</p>
                    <p className="text-lg text-gray-900">{result.indicator_type.toUpperCase()}</p>
                  </div>
                  <div className="animate-fade-in-delay-3">
                    <p className="text-sm text-gray-600">Detection Ratio</p>
                    <p className="text-lg text-gray-900">{result.detection_ratio}</p>
                  </div>
                  <div className="animate-fade-in-delay-4">
                    <p className="text-sm text-gray-600">Status</p>
                    <span className={`inline-flex px-2 py-1 text-sm font-medium rounded-full transition-all ${
                      result.status === 'completed' ? 'text-green-700 bg-green-100' : 'text-yellow-700 bg-yellow-100'
                    }`}>
                      {result.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                {result.reputation && (
                  <div className="mb-4 animate-fade-in-delay-5">
                    <p className="text-sm text-gray-600">Reputation</p>
                    <p className="text-lg text-gray-900">{result.reputation}</p>
                  </div>
                )}

                {result.categories && result.categories.length > 0 && (
                  <div className="mb-4 animate-fade-in-delay-6">
                    <p className="text-sm text-gray-600 mb-2">Categories</p>
                    <div className="flex flex-wrap gap-2">                      {result.categories.map((category, index) => (
                        <span 
                          key={index} 
                          className={`inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full transition-all hover:bg-blue-200 animate-scale-in animate-delay-${Math.min(index * 100, 500)}`}
                        >
                          {category}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {result.tags && result.tags.length > 0 && (
                  <div className="mb-4 animate-fade-in-delay-7">
                    <p className="text-sm text-gray-600 mb-2">Tags</p>
                    <div className="flex flex-wrap gap-2">                      {result.tags.map((tag, index) => (
                        <span 
                          key={index} 
                          className={`inline-flex px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full transition-all hover:bg-gray-200 animate-scale-in animate-delay-${Math.min(index * 100, 500)}`}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Threat Score */}
              {result.threat_score && (
                <div className="animate-slide-up-delay-1">
                  <ThreatScoreCard score={result.threat_score} />
                </div>
              )}

              {/* Vendor Results */}
              {result.vendor_results && result.vendor_results.length > 0 && (
                <div className="animate-slide-up-delay-2">
                  <VendorResultsCard results={result.vendor_results} />
                </div>
              )}

              {/* Geolocation */}
              {result.geolocation && (
                <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover animate-slide-up-delay-3">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Geolocation Information</h3>
                  <div className="grid grid-cols-2 gap-4">                    {Object.entries(result.geolocation).map(([key, value], index) => (
                      <div key={key} className={`animate-fade-in animate-delay-${Math.min(index * 150, 500)}`}>
                        <p className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</p>
                        <p className="text-sm text-gray-900">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              {(result.first_seen || result.last_seen) && (
                <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover animate-slide-up-delay-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Timeline</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {result.first_seen && (
                      <div className="animate-fade-in-delay-1">
                        <p className="text-sm text-gray-600">First Seen</p>
                        <p className="text-sm text-gray-900">{new Date(result.first_seen).toLocaleString()}</p>
                      </div>
                    )}
                    {result.last_seen && (
                      <div className="animate-fade-in-delay-2">
                        <p className="text-sm text-gray-600">Last Seen</p>
                        <p className="text-sm text-gray-900">{new Date(result.last_seen).toLocaleString()}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
