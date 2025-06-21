import React from 'react';

// Base skeleton component
export const Skeleton: React.FC<{ 
  className?: string; 
  variant?: 'text' | 'rectangular' | 'circular';
  height?: number | string;
  width?: number | string;
  count?: number;
}> = ({ 
  className = '', 
  variant = 'rectangular',
  height = 20,
  width = '100%',
  count = 1
}) => {
  const baseClasses = 'animate-pulse bg-gray-200 rounded';
  
  const variantClasses = {
    text: 'h-4',
    rectangular: 'h-5',
    circular: 'rounded-full'
  };

  const skeletonElement = (
    <div 
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={{ height, width }}
    />
  );

  if (count === 1) {
    return skeletonElement;
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: count }, (_, index) => (
        <div key={index}>
          {skeletonElement}
        </div>
      ))}
    </div>
  );
};

// Card skeleton for dashboard stats
export const StatCardSkeleton: React.FC = () => (
  <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <Skeleton width="60%" height={16} className="mb-2" />
        <Skeleton width="40%" height={24} className="mb-2" />
        <Skeleton width="50%" height={14} />
      </div>
      <Skeleton variant="circular" width={48} height={48} />
    </div>
  </div>
);

// Table row skeleton
export const TableRowSkeleton: React.FC<{ columns?: number }> = ({ columns = 4 }) => (
  <tr className="border-b border-gray-200">
    {Array.from({ length: columns }, (_, index) => (
      <td key={index} className="px-6 py-4">
        <Skeleton height={16} />
      </td>
    ))}
  </tr>
);

// Analysis result skeleton
export const AnalysisResultSkeleton: React.FC = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="border-b border-gray-200 pb-4">
      <Skeleton width="30%" height={32} className="mb-2" />
      <Skeleton width="60%" height={20} />
    </div>

    {/* Score section */}
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="md:col-span-1">
        <Skeleton width="80%" height={20} className="mb-4" />
        <div className="relative">
          <Skeleton variant="circular" width={120} height={120} className="mx-auto mb-4" />
          <Skeleton width="60%" height={24} className="mx-auto" />
        </div>
      </div>
      <div className="md:col-span-2 space-y-4">
        <Skeleton width="40%" height={20} />
        <Skeleton count={3} height={16} className="space-y-2" />
      </div>
    </div>

    {/* Vendor results */}
    <div>
      <Skeleton width="30%" height={24} className="mb-4" />
      <div className="space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
            <div className="flex items-center space-x-3">
              <Skeleton variant="circular" width={32} height={32} />
              <Skeleton width={100} height={16} />
            </div>
            <Skeleton width={80} height={20} />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// History table skeleton
export const HistoryTableSkeleton: React.FC = () => (
  <div className="bg-white shadow overflow-hidden sm:rounded-md">
    <div className="px-4 py-5 sm:p-6">
      <Skeleton width="40%" height={24} className="mb-6" />
      
      {/* Table header */}
      <div className="grid grid-cols-6 gap-4 py-3 border-b border-gray-200 mb-4">
        <Skeleton width="80%" height={16} />
        <Skeleton width="60%" height={16} />
        <Skeleton width="70%" height={16} />
        <Skeleton width="50%" height={16} />
        <Skeleton width="80%" height={16} />
        <Skeleton width="40%" height={16} />
      </div>

      {/* Table rows */}
      <div className="space-y-4">
        {Array.from({ length: 10 }, (_, index) => (
          <div key={index} className="grid grid-cols-6 gap-4 py-3">
            <Skeleton height={16} />
            <Skeleton height={16} />
            <Skeleton height={16} />
            <Skeleton height={16} />
            <Skeleton height={16} />
            <Skeleton height={16} />
          </div>
        ))}
      </div>
    </div>
  </div>
);

// Form skeleton
export const FormSkeleton: React.FC = () => (
  <div className="space-y-6">
    <div>
      <Skeleton width="20%" height={16} className="mb-2" />
      <Skeleton height={40} />
    </div>
    <div>
      <Skeleton width="30%" height={16} className="mb-2" />
      <Skeleton height={40} />
    </div>
    <Skeleton width="30%" height={40} />
  </div>
);

// Page loading skeleton
export const PageLoadingSkeleton: React.FC<{ 
  title?: boolean;
  stats?: boolean;
  table?: boolean;
  form?: boolean;
}> = ({ 
  title = true, 
  stats = false, 
  table = false, 
  form = false 
}) => (
  <div className="min-h-screen bg-gray-50">
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        {title && (
          <div className="mb-8">
            <Skeleton width="40%" height={36} className="mb-2" />
            <Skeleton width="60%" height={20} />
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </div>
        )}

        {table && <HistoryTableSkeleton />}
        {form && <FormSkeleton />}
      </div>
    </div>
  </div>
);
