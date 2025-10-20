'use client';

import { useState } from 'react';
import { authenticatedFetch } from '../../utils/auth';
import { config } from '../../utils/config';
import QuickSightEmbedded from '../components/QuickSightEmbedded';

export default function TestQuickSightPage() {
  const [testResults, setTestResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedDashboard, setSelectedDashboard] = useState<string>('69aad539-a2da-4028-999a-472c19ff8348');
  const [customDashboardId, setCustomDashboardId] = useState<string>('69aad539-a2da-4028-999a-472c19ff8348');

  const runTests = async () => {
    setLoading(true);
    const results: any = {
      timestamp: new Date().toISOString(),
      tests: {}
    };

    try {
      // Test 1: Check QuickSight status
      console.log('Testing QuickSight status...');
      try {
        const statusResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/status`);
        const statusData = await statusResponse.json();
        results.tests.status = {
          success: statusResponse.ok,
          data: statusData,
          error: statusResponse.ok ? null : 'Status check failed'
        };
      } catch (error) {
        results.tests.status = {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }

      // Test 2: List dashboards
      console.log('Testing dashboard listing...');
      try {
        const dashboardsResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/dashboards`);
        const dashboardsData = await dashboardsResponse.json();
        results.tests.dashboards = {
          success: dashboardsResponse.ok,
          data: dashboardsData,
          error: dashboardsResponse.ok ? null : 'Dashboard listing failed'
        };
        
        // Auto-select first dashboard if available
        if (dashboardsResponse.ok && dashboardsData.data?.dashboards?.length > 0) {
          setSelectedDashboard(dashboardsData.data.dashboards[0].dashboard_id);
        }
      } catch (error) {
        results.tests.dashboards = {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }

      // Test 3: Generate embed URL
      console.log('Testing embed URL generation...');
      const testDashboardId = customDashboardId || '69aad539-a2da-4028-999a-472c19ff8348';
      try {
        const embedResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/embed-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dashboardId: testDashboardId })
        });
        const embedData = await embedResponse.json();
        results.tests.embedUrl = {
          success: embedResponse.ok,
          data: embedData,
          error: embedResponse.ok ? null : 'Embed URL generation failed'
        };
      } catch (error) {
        results.tests.embedUrl = {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }

      setTestResults(results);
    } catch (error) {
      console.error('Test execution failed:', error);
      setTestResults({
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
        tests: {}
      });
    } finally {
      setLoading(false);
    }
  };

  const TestResult = ({ title, result }: { title: string; result: any }) => (
    <div className="border rounded-lg p-4 mb-4">
      <div className="flex items-center mb-2">
        <span className={`w-3 h-3 rounded-full mr-3 ${result?.success ? 'bg-green-500' : 'bg-red-500'}`}></span>
        <h3 className="font-semibold">{title}</h3>
      </div>
      
      {result?.success ? (
        <div className="text-green-700 bg-green-50 p-3 rounded">
          <p className="font-medium">✅ Success</p>
          {result.data && (
            <pre className="mt-2 text-xs overflow-x-auto">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          )}
        </div>
      ) : (
        <div className="text-red-700 bg-red-50 p-3 rounded">
          <p className="font-medium">❌ Failed</p>
          <p className="text-sm mt-1">{result?.error || 'Unknown error'}</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">QuickSight Integration Test</h1>
          <p className="text-gray-600 mb-6">
            This page tests the QuickSight integration functionality. Use this to validate that 
            the backend and frontend are properly configured.
          </p>

          {/* Test Controls */}
          <div className="border-t pt-6">
            <div className="flex flex-col sm:flex-row gap-4 mb-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Test Dashboard ID
                </label>
                <input
                  type="text"
                  value={customDashboardId}
                  onChange={(e) => setCustomDashboardId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter dashboard ID to test"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={runTests}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold py-2 px-6 rounded"
                >
                  {loading ? 'Running Tests...' : 'Run Tests'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Test Results */}
        {testResults && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Test Results</h2>
            <p className="text-sm text-gray-500 mb-6">
              Executed at: {new Date(testResults.timestamp).toLocaleString()}
            </p>

            {testResults.error ? (
              <div className="text-red-700 bg-red-50 p-4 rounded">
                <p className="font-medium">❌ Test execution failed</p>
                <p className="text-sm mt-1">{testResults.error}</p>
              </div>
            ) : (
              <div className="space-y-4">
                <TestResult title="QuickSight Status Check" result={testResults.tests.status} />
                <TestResult title="Dashboard Listing" result={testResults.tests.dashboards} />
                <TestResult title="Embed URL Generation" result={testResults.tests.embedUrl} />
              </div>
            )}
          </div>
        )}

        {/* Simple Iframe Test */}
        {testResults?.tests?.embedUrl?.success && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Simple Iframe Test</h2>
            <p className="text-gray-600 mb-4">
              Testing if the embed URL works in a simple iframe:
            </p>
            <div className="border rounded-lg overflow-hidden" style={{ height: '400px' }}>
              <iframe
                src={testResults.tests.embedUrl.data.embedUrl}
                width="100%"
                height="100%"
                frameBorder="0"
                title="QuickSight Dashboard Test"
                onLoad={() => console.log('Iframe loaded')}
                onError={(e) => console.error('Iframe error:', e)}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              If you can see the dashboard above, the embed URL is working correctly.
            </p>
          </div>
        )}

        {/* Dashboard Embedding Test */}
        {selectedDashboard && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Dashboard Embedding Test</h2>
            <p className="text-gray-600 mb-4">
              Testing dashboard embedding with ID: <code className="bg-gray-100 px-2 py-1 rounded">{selectedDashboard}</code>
            </p>
            
            <div className="border rounded-lg overflow-hidden">
              <QuickSightEmbedded
                dashboardId={selectedDashboard}
                height="600px"
                width="100%"
                onError={(error) => {
                  console.error('Dashboard embedding error:', error);
                  alert('Dashboard Error: ' + error);
                }}
                onLoad={() => {
                  console.log('Dashboard loaded successfully');
                  alert('Dashboard loaded successfully!');
                }}
              />
            </div>
          </div>
        )}

        {/* Manual Dashboard Test */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Manual Dashboard Test</h2>
          <div className="flex gap-4 mb-4">
            <input
              type="text"
              value={customDashboardId}
              onChange={(e) => setCustomDashboardId(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter dashboard ID"
            />
            <button
              onClick={() => setSelectedDashboard(customDashboardId)}
              className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
            >
              Load Dashboard
            </button>
          </div>
        </div>

        {/* Debug Information */}
        <div className="bg-white rounded-lg shadow p-6 mt-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Debug Information</h2>
          <div className="space-y-2 text-sm">
            <p><strong>API Base URL:</strong> {config.apiBaseUrl}</p>
            <p><strong>Environment:</strong> {config.isDevelopment ? 'Development' : 'Production'}</p>
            <p><strong>Current Time:</strong> {new Date().toISOString()}</p>
          </div>
          
          {testResults && (
            <div className="mt-4">
              <h3 className="font-medium mb-2">Raw Test Results:</h3>
              <pre className="bg-gray-100 p-4 rounded text-xs overflow-x-auto">
                {JSON.stringify(testResults, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}