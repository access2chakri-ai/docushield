'use client';

import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../../utils/auth';
import { config } from '../../utils/config';
import QuickSightNavigation from '../components/QuickSightNavigation';

interface StatusData {
  status: string;
  service: string;
  dashboards_available: number;
  account_id: string;
  region: string;
  error?: string;
}

interface Dashboard {
  dashboard_id: string;
  name: string;
  embed_url?: string;
  created_time?: string;
  last_updated?: string;
}

export default function QuickSightStatusPage() {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load status
      const statusResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/status`);
      const statusData = await statusResponse.json();
      setStatus(statusData);

      // Load dashboards
      const dashboardsResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/dashboards`);
      const dashboardsData = await dashboardsResponse.json();
      
      if (dashboardsResponse.ok && dashboardsData.success) {
        setDashboards(dashboardsData.data.dashboards);
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load status';
      setError(errorMessage);
      console.error('Error loading status:', err);
    } finally {
      setLoading(false);
    }
  };

  const openDashboard = (dashboardId: string) => {
    const url = `https://us-east-1.quicksight.aws.amazon.com/sn/dashboards/${dashboardId}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading QuickSight status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900">QuickSight Integration Status</h1>
            <p className="mt-2 text-gray-600">
              Monitor the health and configuration of your QuickSight integration
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <QuickSightNavigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error Loading Status</h3>
                <p className="mt-2 text-sm text-red-700">{error}</p>
                <div className="mt-4">
                  <button
                    onClick={loadStatus}
                    className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded text-sm"
                  >
                    Retry
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Service Status */}
            {status && (
              <div className="bg-white rounded-lg shadow mb-8">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Service Status</h2>
                </div>
                <div className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="text-center">
                      <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-3 ${
                        status.status === 'healthy' ? 'bg-green-100' : 'bg-yellow-100'
                      }`}>
                        <div className={`w-6 h-6 rounded-full ${
                          status.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'
                        }`}></div>
                      </div>
                      <p className="text-sm font-medium text-gray-900">Overall Status</p>
                      <p className={`text-sm ${
                        status.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'
                      }`}>
                        {status.status === 'healthy' ? 'Healthy' : 'Warning'}
                      </p>
                    </div>

                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto bg-blue-100 rounded-full flex items-center justify-center mb-3">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      </div>
                      <p className="text-sm font-medium text-gray-900">Dashboards</p>
                      <p className="text-sm text-blue-600">{status.dashboards_available} Available</p>
                    </div>

                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto bg-purple-100 rounded-full flex items-center justify-center mb-3">
                        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <p className="text-sm font-medium text-gray-900">Region</p>
                      <p className="text-sm text-purple-600">{status.region}</p>
                    </div>

                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto bg-gray-100 rounded-full flex items-center justify-center mb-3">
                        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                      <p className="text-sm font-medium text-gray-900">Account</p>
                      <p className="text-sm text-gray-600">{status.account_id}</p>
                    </div>
                  </div>

                  {status.error && (
                    <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <div className="flex">
                        <svg className="h-5 w-5 text-yellow-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        <div className="ml-3">
                          <h3 className="text-sm font-medium text-yellow-800">Service Warning</h3>
                          <p className="mt-1 text-sm text-yellow-700">{status.error}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* QuickSight Edition Notice */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">QuickSight Standard Edition</h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <p>Your AWS account is using QuickSight Standard Edition. Dashboard embedding requires Enterprise Edition.</p>
                    <p className="mt-2">
                      <strong>Current behavior:</strong> Dashboards will open in new tabs instead of embedding directly in the page.
                      This provides the same analytics functionality with a slightly different user experience.
                    </p>
                  </div>
                  <div className="mt-4">
                    <a
                      href="https://aws.amazon.com/quicksight/pricing/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-500 text-sm font-medium"
                    >
                      Learn about QuickSight Enterprise Edition →
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Available Dashboards */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Available Dashboards</h2>
                <p className="mt-1 text-sm text-gray-500">
                  Click on any dashboard to open it in a new tab
                </p>
              </div>
              
              {dashboards.length === 0 ? (
                <div className="p-6 text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No dashboards found</h3>
                  <p className="mt-1 text-sm text-gray-500">Create dashboards in the AWS QuickSight console.</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {dashboards.map((dashboard) => (
                    <div key={dashboard.dashboard_id} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div className="flex-shrink-0">
                            <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                              <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
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
                            onClick={() => openDashboard(dashboard.dashboard_id)}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center"
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                            Open Dashboard
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="mt-8 flex justify-center space-x-4">
              <button
                onClick={loadStatus}
                className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded"
              >
                Refresh Status
              </button>
              <a
                href="/analytics"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
              >
                Go to Analytics
              </a>
              <a
                href="/test-quicksight"
                className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
              >
                Run Tests
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}