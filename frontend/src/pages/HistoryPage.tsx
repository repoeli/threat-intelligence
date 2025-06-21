import React from 'react';

export default function HistoryPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-gray-900">Analysis History</h1>
        <p className="mt-2 text-gray-600">View your past threat analyses</p>
        
        <div className="mt-8 card">
          <h2 className="text-xl font-semibold">History Table</h2>
          <p className="text-gray-600">This will contain the history table</p>
        </div>
      </div>
    </div>
  );
}
