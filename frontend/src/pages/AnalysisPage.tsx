import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient } from '../services/api';
import { AnalysisRequest, ThreatIntelligenceResult, IndicatorType } from '../types';

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
      case 'critical':
      case 'malicious': return 'text-red-900 bg-red-200';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Threat Assessment</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-600">Threat Score</p>
          <p className="text-2xl font-bold text-gray-900">{threatScore}/100</p>
        </div>
        
        <div>
          <p className="text-sm text-gray-600">Risk Level</p>
          <span className={`inline-flex px-2 py-1 text-sm font-medium rounded-full ${getRiskColor(riskLevel)}`}>
            {riskLevel.toUpperCase()}
          </span>
        </div>
        
        <div className="col-span-2">
          <p className="text-sm text-gray-600">Confidence</p>
          <div className="mt-1 bg-gray-200 rounded-full h-2 relative overflow-hidden">
            <div className={`bg-blue-500 h-full rounded-full transition-all duration-300 ${
              confidence >= 0.8 ? 'w-4/5' :
              confidence >= 0.6 ? 'w-3/5' :
              confidence >= 0.4 ? 'w-2/5' :
              confidence >= 0.2 ? 'w-1/5' : 'w-1/12'
            }`} />
          </div>
          <p className="text-sm text-gray-500 mt-1">{Math.round(confidence * 100)}%</p>
        </div>
        
        <div className="col-span-2">
          <p className="text-sm text-gray-600">Analysis Reasoning</p>
          <p className="text-sm text-gray-900 mt-1">{reasoning}</p>
        </div>
        
        {/* Show threat factors if available */}
        {score?.factors && (
          <div className="col-span-2">
            <p className="text-sm text-gray-600">Source Breakdown</p>
            <div className="mt-2 space-y-1">
              {Object.entries(score.factors).map(([source, value]: [string, any]) => (
                <div key={source} className="flex justify-between text-sm">
                  <span className="text-gray-600 capitalize">{source}:</span>
                  <span className="text-gray-900">{value}/100</span>
                </div>
              ))}
            </div>
          </div>
        )}
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
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Vendor Analysis</h3>
      
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {results.map((result, index) => (
          <div key={index} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-b-0">
            <div className="flex-1">
              <p className="font-medium text-gray-900">{result.vendor}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getVerdictColor(result.result, result.category)}`}>
                  {result.result}
                </span>
                {result.category && (
                  <span className="text-xs text-gray-500">
                    ({result.category})
                  </span>
                )}
              </div>
            </div>
            {result.engine_version && (
              <div className="text-right">
                <p className="text-xs text-gray-500">
                  Engine: {result.engine_version}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-sm text-gray-600">
          Total vendors: {results.length} | 
          Clean: {results.filter(r => r.result === 'clean').length} | 
          Malicious: {results.filter(r => r.result === 'malicious').length} |
          Unrated: {results.filter(r => r.result === 'unrated').length}
        </p>
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
    }

    analysisMutation.mutate(formData);
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
          <h1 className="text-3xl font-bold text-gray-900">Threat Analysis</h1>
          <p className="mt-2 text-gray-600">Analyze indicators for potential threats and security risks</p>
          
          {/* Analysis Form */}
          <div className="mt-8 bg-white rounded-lg border border-gray-200 p-6">
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
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter IP address, domain, URL, or file hash..."
                  value={formData.indicator}
                  onChange={handleChange}
                />
                {detectedType && (
                  <p className="mt-1 text-sm text-green-600">
                    ✓ Detected as: {detectedType.toUpperCase()}
                  </p>
                )}
              </div>

              <div className="flex items-center">
                <input
                  id="include_raw_data"
                  name="include_raw_data"
                  type="checkbox"
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  checked={formData.include_raw_data}
                  onChange={handleChange}
                />
                <label htmlFor="include_raw_data" className="ml-2 block text-sm text-gray-700">
                  Include raw vendor data in response
                </label>
              </div>

              <div className="flex space-x-3">
                <button
                  type="submit"
                  disabled={analysisMutation.isPending || !formData.indicator.trim()}
                  className="bg-blue-600 text-white py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    className="bg-gray-200 text-gray-700 py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
                  >
                    Clear Results
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Analysis Results */}
          {result && (
            <div className="mt-8 space-y-6">
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Analysis Results</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div>
                    <p className="text-sm text-gray-600">Analyzed Indicator</p>
                    <p className="font-mono text-lg text-gray-900 break-all">{result.indicator}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Indicator Type</p>
                    <p className="text-lg text-gray-900">{result.indicator_type.toUpperCase()}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Detection Ratio</p>
                    <p className="text-lg text-gray-900">{result.detection_ratio}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Status</p>
                    <span className={`inline-flex px-2 py-1 text-sm font-medium rounded-full ${
                      result.status === 'completed' ? 'text-green-700 bg-green-100' : 'text-yellow-700 bg-yellow-100'
                    }`}>
                      {result.status.toUpperCase()}
                    </span>
                  </div>
                </div>

                {result.reputation && (
                  <div className="mb-4">
                    <p className="text-sm text-gray-600">Reputation</p>
                    <p className="text-lg text-gray-900">{result.reputation}</p>
                  </div>
                )}

                {result.categories && result.categories.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm text-gray-600 mb-2">Categories</p>
                    <div className="flex flex-wrap gap-2">
                      {result.categories.map((category, index) => (
                        <span key={index} className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                          {category}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {result.tags && result.tags.length > 0 && (
                  <div className="mb-4">
                    <p className="text-sm text-gray-600 mb-2">Tags</p>
                    <div className="flex flex-wrap gap-2">
                      {result.tags.map((tag, index) => (
                        <span key={index} className="inline-flex px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Threat Score */}
              {result.threat_score && (
                <ThreatScoreCard score={result.threat_score} />
              )}

              {/* Vendor Results */}
              {result.vendor_results && result.vendor_results.length > 0 && (
                <VendorResultsCard results={result.vendor_results} />
              )}

              {/* Geolocation */}
              {result.geolocation && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Geolocation Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(result.geolocation).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</p>
                        <p className="text-sm text-gray-900">{String(value)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeline */}
              {(result.first_seen || result.last_seen) && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Timeline</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {result.first_seen && (
                      <div>
                        <p className="text-sm text-gray-600">First Seen</p>
                        <p className="text-sm text-gray-900">{new Date(result.first_seen).toLocaleString()}</p>
                      </div>
                    )}
                    {result.last_seen && (
                      <div>
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
