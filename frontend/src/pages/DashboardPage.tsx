import React from 'react';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">Welcome to your threat intelligence dashboard</p>
          
          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900">Quick Analysis</h3>
              <p className="mt-2 text-sm text-gray-600">Analyze indicators quickly</p>
            </div>
            
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
              <p className="mt-2 text-sm text-gray-600">View your latest analyses</p>
            </div>
            
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900">Statistics</h3>
              <p className="mt-2 text-sm text-gray-600">View usage statistics</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
