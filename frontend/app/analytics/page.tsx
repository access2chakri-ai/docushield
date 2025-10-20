'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { authenticatedFetch } from '../../utils/auth';
import { config } from '../../utils/config';
import QuickSightEmbedded from '../components/QuickSightEmbedded';
import QuickSightNavigation from '../components/QuickSightNavigation';

interface Dashboard {
  dashboard_id: string;
  name: string;
  embed_url?: string;
  created_time?: string;
  last_updated?: string;
}

interface DashboardsResponse {
  success: boolean;
  data: {
    user_id: string;
    dashboards: Dashboard[];
    total_count: number;
  };
}

export default function AnalyticsPage() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [selectedDashboard, setSelectedDashboard] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quicksightStatus, setQuicksightStatus] = useState<any>(null);


  useEffect(() => {
    loadDashboards();
    checkQuickSightStatus();
  }, []);

  const loadDashboards = async () => {
    try {
      setLoading(true);
      
      // 🔑 KEY: Get current user context for user-specific dashboards
      let currentUserId = 'default-user';
      let userData = { user_id: 'default-user', name: 'Default User', email: 'user@docushield.com' };
      
      try {
        // First try to extract user from JWT token (more reliable)
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (token) {
          try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.user_id) {
              currentUserId = payload.user_id;
              userData = {
                user_id: payload.user_id,
                name: payload.name || payload.email?.split('@')[0] || 'User',
                email: payload.email || 'user@docushield.com'
              };
              console.log('🔑 Extracted user from JWT token:', userData);
            }
          } catch (tokenError) {
            console.warn('Could not parse JWT token:', tokenError);
          }
        }
        
        // If token extraction failed, try API endpoint as fallback
        if (currentUserId === 'default-user') {
          console.log('🔍 Attempting to get user profile from API...');
          const userResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/user/profile`);
          
          if (userResponse.ok) {
            const apiUserData = await userResponse.json();
            currentUserId = apiUserData.user_id;
            userData = apiUserData;
            console.log('✅ Got user profile from API:', userData);
          } else {
            console.warn('❌ User profile API failed, using token data');
          }
        }
      } catch (userError) {
        console.warn('Could not get user info:', userError);
      }
      
      console.log('🔍 Loading dashboards for user:', currentUserId);
      
      // Load user-specific dashboards
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/dashboards?user_id=${currentUserId}`);
      
      if (!response.ok) {
        throw new Error('Failed to load dashboards');
      }

      const data: DashboardsResponse = await response.json();
      setDashboards(data.data.dashboards);
      
      console.log('📊 Loaded dashboards:', data.data.dashboards.length, 'for user:', currentUserId);
      
      // Auto-select first dashboard if available
      if (data.data.dashboards.length > 0) {
        setSelectedDashboard(data.data.dashboards[0].dashboard_id);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load user-specific dashboards';
      
      // If API endpoints don't exist yet, show helpful message
      if (errorMessage.includes('Not Found') || errorMessage.includes('404')) {
        setError('Dashboard API endpoints not configured yet. Please restart your backend server to load the new routes.');
      } else {
        setError(errorMessage);
      }
      
      console.error('Error loading dashboards:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkQuickSightStatus = async () => {
    try {
      // 🔑 KEY: Include user context in status check
      let userId = 'default-user';
      
      // Extract user ID from JWT token
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          if (payload.user_id) {
            userId = payload.user_id;
          }
        } catch (tokenError) {
          console.warn('Could not parse token for status check');
        }
      }
      
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/status?user_id=${userId}`);
      const status = await response.json();
      setQuicksightStatus(status);
      
      console.log('📊 QuickSight status for user:', userId, status);
    } catch (err) {
      console.error('Error checking QuickSight status:', err);
    }
  };

  const handleDashboardError = (error: string) => {
    console.error('Dashboard error:', error);
  };

  const handleDashboardLoad = () => {
    console.log('Dashboard loaded successfully');
  };

  if (loading) {
    return (
      <div className="min-h-screen relative" style={{
        backgroundImage: 'url(/backgrounds/analytics-bg.svg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}>
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm"></div>
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="text-center bg-white/90 backdrop-blur-md rounded-2xl p-12 shadow-xl border border-white/20">
            <div className="relative mb-8">
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-200 border-t-blue-600 mx-auto"></div>
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 opacity-20 animate-pulse"></div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Loading Analytics Dashboard</h3>
            <p className="text-gray-600">Preparing your personalized insights...</p>
            <div className="mt-6 flex justify-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen relative" style={{
        backgroundImage: 'url(/backgrounds/analytics-bg.svg)',
        backgroundSize: 'cover',
        backgroundPosition: 'center'
      }}>
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm"></div>
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="text-center max-w-lg bg-white/90 backdrop-blur-md rounded-2xl p-12 shadow-xl border border-white/20">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">Analytics Unavailable</h3>
            <p className="text-gray-600 mb-8">{error}</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={loadDashboards}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                Try Again
              </button>
              <Link
                href="/upload"
                className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                Upload Documents
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative" style={{
      backgroundImage: 'url(/backgrounds/analytics-bg.svg)',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    }}>
      {/* Overlay for better readability */}
      <div className="absolute inset-0 bg-white/80 backdrop-blur-sm"></div>
      
      {/* Header */}
      <div className="relative z-10 bg-white/90 backdrop-blur-md shadow-lg border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Analytics Dashboard
                </h1>
                <p className="mt-3 text-lg text-gray-600">
                  Real-time insights and analytics for your document intelligence platform
                </p>

              </div>
              
              {/* Quick Actions */}
              <div className="flex space-x-3">
                <button
                  onClick={loadDashboards}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Refresh</span>
                </button>
                <Link
                  href="/upload"
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>Add Documents</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <QuickSightNavigation />

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">


        {/* Dashboard Selection */}
        {dashboards.length > 0 && (
          <div className="mb-4">
            <label htmlFor="dashboard-select" className="block text-sm font-medium text-gray-700 mb-2">
              Select Dashboard
            </label>
            <select
              id="dashboard-select"
              value={selectedDashboard || ''}
              onChange={(e) => setSelectedDashboard(e.target.value)}
              className="block w-full max-w-md px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              {dashboards.map((dashboard) => (
                <option key={dashboard.dashboard_id} value={dashboard.dashboard_id}>
                  {dashboard.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* QuickSight Edition Notice */}
        {quicksightStatus && quicksightStatus.status === 'error' && quicksightStatus.error?.includes('UnsupportedPricingPlanException') && (
          <div className="mb-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">QuickSight Standard Edition</h3>
                  <p className="mt-1 text-sm text-blue-700">
                    Dashboard embedding requires Enterprise Edition. Dashboards will open in new tabs instead.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Content */}
        {dashboards.length === 0 ? (
          <div className="text-center py-16">
            <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-12 border border-white/20">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <svg
                  className="w-10 h-10 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Analytics Dashboard Setup</h3>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">
                Your analytics dashboards are being prepared. Upload some documents to start generating insights and visualizations.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={loadDashboards}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                  Refresh Dashboards
                </button>
                <Link
                  href="/upload"
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                  Upload Documents
                </Link>
              </div>
            </div>
          </div>
        ) : selectedDashboard ? (
          <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-white/20 overflow-hidden min-h-[calc(100vh-300px)]">
            <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                {dashboards.find(d => d.dashboard_id === selectedDashboard)?.name || 'Dashboard'}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Real-time analytics and insights for your documents
              </p>
            </div>
            <div className="w-full" style={{ height: 'calc(100vh - 220px)', minHeight: '750px' }}>
              <QuickSightEmbedded
                dashboardId={selectedDashboard}
                height="100%"
                width="100%"
                onError={handleDashboardError}
                onLoad={handleDashboardLoad}
              />
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="bg-white/90 backdrop-blur-md rounded-xl p-8 border border-white/20">
              <p className="text-gray-600">Please select a dashboard to view your analytics.</p>
            </div>
          </div>
        )}

        {/* Dashboard List - Only show if no dashboard is selected or multiple dashboards */}
        {dashboards.length > 1 && !selectedDashboard && (
          <div className="mt-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Available Dashboards</h2>
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {dashboards.map((dashboard) => (
                  <li key={dashboard.dashboard_id}>
                    <div className="px-4 py-4 flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                            <svg
                              className="h-6 w-6 text-blue-600"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                              />
                            </svg>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {dashboard.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {dashboard.dashboard_id}
                          </div>
                          {dashboard.last_updated && (
                            <div className="text-xs text-gray-400">
                              Last updated: {new Date(dashboard.last_updated).toLocaleDateString()}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setSelectedDashboard(dashboard.dashboard_id)}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
                        >
                          View Dashboard
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}