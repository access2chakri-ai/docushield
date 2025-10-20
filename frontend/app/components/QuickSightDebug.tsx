'use client';

import { useState } from 'react';
import { authenticatedFetch } from '../../utils/auth';
import { config } from '../../utils/config';

export default function QuickSightDebug() {
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const testEmbedUrl = async () => {
    setLoading(true);
    try {
      console.log('Testing embed URL generation...');
      
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/embed-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dashboardId: '69aad539-a2da-4028-999a-472c19ff8348' })
      });

      const data = await response.json();
      console.log('Response:', data);
      
      setDebugInfo({
        success: response.ok,
        status: response.status,
        data: data,
        embedUrl: data.embedUrl,
        isEmbedUrl: data.isEmbedUrl,
        urlType: data.embedUrl?.includes('/embed/') ? 'embed' : 'public'
      });
      
    } catch (error) {
      console.error('Error:', error);
      setDebugInfo({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setLoading(false);
    }
  };

  const testDirectAPI = async () => {
    setLoading(true);
    try {
      console.log('Testing direct API call...');
      
      // Test the status endpoint first
      const statusResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/status`);
      const statusData = await statusResponse.json();
      
      // Test the dashboards endpoint
      const dashboardsResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/dashboards`);
      const dashboardsData = await dashboardsResponse.json();
      
      setDebugInfo({
        success: true,
        status: {
          response: statusResponse.ok,
          data: statusData
        },
        dashboards: {
          response: dashboardsResponse.ok,
          data: dashboardsData
        }
      });
      
    } catch (error) {
      console.error('Direct API Error:', error);
      setDebugInfo({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">QuickSight Debug Panel</h2>
      
      <div className="space-y-4">
        <button
          onClick={testEmbedUrl}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Testing...' : 'Test Embed URL Generation'}
        </button>
        
        <button
          onClick={testDirectAPI}
          className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded ml-2"
        >
          Test Direct API Calls
        </button>
      </div>

      {debugInfo && (
        <div className="mt-6">
          <h3 className="font-semibold mb-2">Debug Results:</h3>
          <pre className="bg-gray-100 p-4 rounded text-sm overflow-x-auto">
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
          
          {debugInfo.embedUrl && (
            <div className="mt-4">
              <h4 className="font-semibold">Embed URL Analysis:</h4>
              <p className="text-sm">
                <strong>URL:</strong> {debugInfo.embedUrl.substring(0, 100)}...
              </p>
              <p className="text-sm">
                <strong>Type:</strong> {debugInfo.urlType}
              </p>
              <p className="text-sm">
                <strong>Contains /embed/:</strong> {debugInfo.embedUrl.includes('/embed/') ? 'Yes' : 'No'}
              </p>
              <p className="text-sm">
                <strong>Contains /sn/dashboards/:</strong> {debugInfo.embedUrl.includes('/sn/dashboards/') ? 'Yes' : 'No'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}