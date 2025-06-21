import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Don't show navbar on login/register pages
  if (!isAuthenticated || location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  const navItems = [
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Analysis', href: '/analysis' },
    { name: 'History', href: '/history' },
  ];  return (
    <nav className="bg-white shadow-lg border-b border-gray-200 sticky top-0 z-50 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and navigation links */}
          <div className="flex items-center">
            <div className="flex-shrink-0 flex items-center group">
              <div className="bg-gradient-to-r from-blue-500 to-indigo-600 p-2 rounded-lg group-hover:scale-110 transition-transform duration-200">
                <span className="text-white text-lg">🛡️</span>
              </div>
              <h1 className="ml-3 text-xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
                Threat Intel
              </h1>
            </div>            
            {/* Navigation links */}
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-all duration-200 transform hover:scale-105 ${
                      isActive
                        ? 'border-blue-500 text-blue-600 shadow-sm'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    }`}
                  >
                    <span className="flex items-center space-x-1">
                      {item.name === 'Dashboard' && <span>📊</span>}
                      {item.name === 'Analysis' && <span>🔍</span>}
                      {item.name === 'History' && <span>📋</span>}
                      <span>{item.name}</span>
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            {/* User info */}
            <div className="flex items-center space-x-3 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-700 animate-fade-in">
              <div className="h-8 w-8 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm">👤</span>
              </div>
              <span className="hidden sm:block font-medium">{user?.email}</span>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-red-50 hover:text-red-600 hover:border-red-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all duration-200 transform hover:scale-105"
            >
              <span className="flex items-center space-x-1">
                <span>🚪</span>
                <span className="hidden sm:block">Logout</span>
              </span>            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className="sm:hidden border-t border-gray-200">
        <div className="pt-2 pb-3 space-y-1 bg-gray-50">
          {navItems.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`block pl-3 pr-4 py-3 border-l-4 text-base font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-50 border-blue-500 text-blue-700'
                    : 'border-transparent text-gray-600 hover:bg-white hover:border-gray-300 hover:text-gray-800'
                }`}
              >
                <span className="flex items-center space-x-2">
                  {item.name === 'Dashboard' && <span>📊</span>}
                  {item.name === 'Analysis' && <span>🔍</span>}
                  {item.name === 'History' && <span>📋</span>}
                  <span>{item.name}</span>
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
