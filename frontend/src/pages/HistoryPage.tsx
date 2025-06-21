import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { AnalysisHistoryItem, HistoryFilters } from '../types';
import { PageLoadingSkeleton } from '../components/SkeletonLoaders';

interface PaginationInfo {
  limit: number;
  offset: number;
  currentPage: number;
}

export default function HistoryPage() {
  const [filters, setFilters] = useState<HistoryFilters>({});
  const [pagination, setPagination] = useState<PaginationInfo>({
    limit: 20,
    offset: 0,
    currentPage: 1
  });
  const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisHistoryItem | null>(null);
  const { data: historyData, isLoading, error, refetch } = useQuery({
    queryKey: ['analysisHistory', pagination, filters],
    queryFn: () => {
      // Clean up filters to remove empty values
      const cleanFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, value]) => value !== undefined && value !== '')
      );
      return apiClient.getAnalysisHistory(pagination.limit, pagination.offset, cleanFilters);
    },
    retry: 1,
    refetchOnWindowFocus: false
  });

  const handleFilterChange = (key: keyof HistoryFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value || undefined
    }));
    setPagination(prev => ({ ...prev, offset: 0, currentPage: 1 }));
  };

  const handlePageChange = (newPage: number) => {
    const newOffset = (newPage - 1) * pagination.limit;
    setPagination(prev => ({
      ...prev,
      currentPage: newPage,
      offset: newOffset
    }));
  };
  const handleExport = () => {
    if (!historyData?.analyses?.length) return;
    
    try {
      const csvContent = [
        ['Date', 'Indicator', 'Type', 'Risk Level', 'Threat Score'].join(','),
        ...historyData.analyses
          .filter(item => item && item.analyzed_at)
          .map(item => [
            formatDate(item.analyzed_at).date,
            item.indicator || '',
            item.indicator_type || '',
            item.risk_level || '',
            (item.threat_score || 0).toString()
          ].join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `threat-analysis-history-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting CSV:', error);
    }
  };
  const getRiskLevelColor = (riskLevel: string) => {
    if (!riskLevel || typeof riskLevel !== 'string') {
      return 'text-gray-600 bg-gray-100';
    }
    switch (riskLevel.toLowerCase()) {
      case 'safe': return 'text-green-600 bg-green-100';
      case 'low': return 'text-yellow-600 bg-yellow-100';
      case 'medium': return 'text-orange-600 bg-orange-100';
      case 'high': return 'text-red-600 bg-red-100';
      case 'critical': return 'text-purple-600 bg-purple-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return { date: 'Invalid Date', time: '--' };
      }
      return {
        date: date.toLocaleDateString(),
        time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
    } catch (error) {
      return { date: 'Invalid Date', time: '--' };
    }
  };

  const totalPages = historyData?.total_analyses ? Math.ceil(historyData.total_analyses / pagination.limit) : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 fade-in">
          <h1 className="text-3xl font-bold text-gray-900">Analysis History</h1>
          <p className="mt-2 text-gray-600">
            View and manage your past threat intelligence analyses
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <PageLoadingSkeleton title={false} stats={true} table={true} />
        )}

        {/* Stats Summary */}
        {historyData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 slide-up">
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover animate-fade-in-delay-1">
              <div className="flex items-center">
                <div className="p-3 rounded-lg bg-blue-100">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Total Analyses</p>
                  <p className="text-2xl font-bold text-gray-900">{historyData.total_analyses}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover animate-fade-in-delay-2">
              <div className="flex items-center">
                <div className="p-3 rounded-lg bg-green-100">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Current Page</p>
                  <p className="text-2xl font-bold text-gray-900">{pagination.currentPage} of {totalPages}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm card-hover animate-fade-in-delay-3">
              <div className="flex items-center">
                <div className="p-3 rounded-lg bg-purple-100">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2h4a1 1 0 011 1v1a1 1 0 01-1 1h-1v12a2 2 0 01-2 2H6a2 2 0 01-2-2V7H3a1 1 0 01-1-1V5a1 1 0 011-1h4z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Subscription</p>
                  <p className="text-2xl font-bold text-gray-900 capitalize">{historyData.subscription}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters and Search */}
        {!isLoading && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-8 card-hover animate-slide-up-delay-1">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div className="flex flex-col sm:flex-row gap-4 flex-1">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Search indicators..."
                    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm form-field-enhanced"
                    value={filters.search || ''}
                    onChange={(e) => handleFilterChange('search', e.target.value)}
                  />
                </div>
                <select
                  className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm form-field-enhanced"
                  value={filters.indicator_type || ''}
                  onChange={(e) => handleFilterChange('indicator_type', e.target.value)}
                  aria-label="Filter by indicator type"
                >
                  <option value="">All Types</option>
                  <option value="ip">IP Address</option>
                  <option value="domain">Domain</option>
                  <option value="url">URL</option>
                  <option value="hash">Hash</option>
                </select>
                <select
                  className="block rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm form-field-enhanced"
                  value={filters.threat_level || ''}
                  onChange={(e) => handleFilterChange('threat_level', e.target.value)}
                  aria-label="Filter by threat level"
                >
                  <option value="">All Risk Levels</option>
                  <option value="safe">Safe</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setFilters({})}
                  className="bg-gray-200 text-gray-700 py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 btn-enhanced"
                >
                  Clear Filters
                </button>
                <button
                  onClick={handleExport}
                  disabled={!historyData?.analyses?.length}
                  className="bg-blue-600 text-white py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                >
                  Export CSV
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Results Table */}
        {!isLoading && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm card-hover animate-slide-up-delay-2">
            {error ? (
              <div className="text-center py-12 animate-fade-in">
                <div className="text-red-600 mb-4">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to load history</h3>
                <p className="text-gray-600 mb-4">There was an error loading your analysis history.</p>
                <button onClick={() => refetch()} className="bg-blue-600 text-white py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 btn-enhanced">
                  Try Again
                </button>
              </div>
            ) : !historyData?.analyses?.length ? (
              <div className="text-center py-12 animate-fade-in">
                <div className="text-gray-400 mb-4">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No analyses found</h3>
                <p className="text-gray-600">
                  {Object.keys(filters).length > 0 
                    ? "No analyses match your current filters. Try adjusting your search criteria."
                    : "You haven't performed any threat analyses yet."
                  }
                </p>
              </div>
            ) : (
              <>                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Indicator</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Level</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Threat Score</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Analyzed At</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">{historyData?.analyses?.map((analysis, index) => {
                        if (!analysis || !analysis.analyzed_at) return null;
                        
                        const dateTime = formatDate(analysis.analyzed_at);
                        const animationDelay = index < 5 ? `animate-fade-in-delay-${index + 1}` : 'animate-fade-in';
                        return (
                          <tr 
                            key={analysis.id || index}
                            className={`hover:bg-gray-50 transition-all ${animationDelay}`}
                          >
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900 max-w-xs truncate" title={analysis.indicator || 'Unknown'}>
                                {analysis.indicator || 'Unknown'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 uppercase transition-all">
                                {analysis.indicator_type || 'unknown'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize transition-all ${getRiskLevelColor(analysis.risk_level || 'unknown')}`}>
                                {analysis.risk_level || 'Unknown'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {analysis.threat_score || 0}/100
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              <div>{dateTime.date}</div>
                              <div className="text-xs text-gray-500">{dateTime.time}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <button
                                onClick={() => setSelectedAnalysis(analysis)}
                                className="text-blue-600 hover:text-blue-900 transition-all btn-enhanced"
                              >
                                View Details
                              </button>
                            </td>
                          </tr>
                        );
                      })}</tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 sm:px-6 animate-fade-in-delay-1">
                    <div className="flex flex-1 justify-between sm:hidden">
                      <button
                        onClick={() => handlePageChange(pagination.currentPage - 1)}
                        disabled={pagination.currentPage === 1}
                        className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => handlePageChange(pagination.currentPage + 1)}
                        disabled={pagination.currentPage === totalPages}
                        className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                      >
                        Next
                      </button>
                    </div>
                    <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm text-gray-700">
                          Showing page <span className="font-medium">{pagination.currentPage}</span> of{' '}
                          <span className="font-medium">{totalPages}</span>
                        </p>
                      </div>
                      <div>
                        <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                          <button
                            onClick={() => handlePageChange(pagination.currentPage - 1)}
                            disabled={pagination.currentPage === 1}
                            className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                          >
                            Previous
                          </button>
                          <button
                            onClick={() => handlePageChange(pagination.currentPage + 1)}
                            disabled={pagination.currentPage === totalPages}
                            className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed btn-enhanced"
                          >
                            Next
                          </button>
                        </nav>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Detail Modal */}
        {selectedAnalysis && (
          <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 animate-fade-in">
            <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white animate-slide-up">
              <div className="mt-3">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Analysis Details</h3>
                  <button
                    onClick={() => setSelectedAnalysis(null)}
                    className="text-gray-400 hover:text-gray-600 transition-all btn-enhanced"
                    aria-label="Close modal"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                <div className="space-y-4">                  <div className="animate-fade-in-delay-1">
                    <label className="block text-sm font-medium text-gray-700">Indicator</label>
                    <p className="mt-1 text-sm text-gray-900 break-all">{selectedAnalysis.indicator || 'Unknown'}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4 animate-fade-in-delay-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Type</label>
                      <p className="mt-1 text-sm text-gray-900 uppercase">{selectedAnalysis.indicator_type || 'unknown'}</p>
                    </div><div>
                      <label className="block text-sm font-medium text-gray-700">Risk Level</label>
                      <span className={`inline-flex mt-1 px-2 py-1 text-xs font-medium rounded-full capitalize ${getRiskLevelColor(selectedAnalysis.risk_level || 'unknown')}`}>
                        {selectedAnalysis.risk_level || 'Unknown'}
                      </span>
                    </div>
                  </div>                  <div className="animate-fade-in-delay-3">
                    <label className="block text-sm font-medium text-gray-700">Threat Score</label>
                    <p className="mt-1 text-sm text-gray-900">{selectedAnalysis.threat_score || 0}/100</p>
                  </div>                  <div className="animate-fade-in-delay-4">
                    <label className="block text-sm font-medium text-gray-700">Analyzed At</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {selectedAnalysis.analyzed_at 
                        ? new Date(selectedAnalysis.analyzed_at).toLocaleString() 
                        : 'Unknown'
                      }
                    </p>
                  </div>

                  {(selectedAnalysis as any).categories && (selectedAnalysis as any).categories.length > 0 && (
                    <div className="animate-fade-in-delay-5">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Categories</label>
                      <div className="flex flex-wrap gap-2">{(selectedAnalysis as any).categories.map((category: string, index: number) => {
                          const animationDelay = index < 5 ? `animate-scale-in-delay-${index + 1}` : 'animate-scale-in';
                          return (
                            <span 
                              key={index} 
                              className={`inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full ${animationDelay}`}
                            >
                              {category}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex justify-end animate-fade-in-delay-6">
                  <button
                    onClick={() => setSelectedAnalysis(null)}
                    className="bg-gray-200 text-gray-700 py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 btn-enhanced"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
