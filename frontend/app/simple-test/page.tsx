'use client';

import { useState, useEffect } from 'react';
import QuickSightEmbedded from '../components/QuickSightEmbedded';
import QuickSightDebug from '../components/QuickSightDebug';
import { config } from '../../utils/config';

export default function SimpleTestPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    console.log('Simple test page mounted');
    console.log('Config:', config);
  }, []);

  if (!mounted) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Simple QuickSight Test</h1>
      <p className="mb-4">Testing with hardcoded dashboard ID:</p>
      
      {/* Debug Panel */}
      <div className="mb-8">
        <QuickSightDebug />
      </div>
      
      {/* Simple Dashboard Test */}
      <div className="border rounded-lg mb-8">
        <div className="p-4 bg-gray-50 border-b">
          <h3 className="font-bold">Dashboard Embedding Test</h3>
          <p className="text-sm text-gray-600">Dashboard ID: 69aad539-a2da-4028-999a-472c19ff8348</p>
        </div>
        <QuickSightEmbedded
          dashboardId="69aad539-a2da-4028-999a-472c19ff8348"
          height="600px"
          width="100%"
          onError={(error) => {
            console.error('Dashboard error:', error);
            alert('Dashboard error: ' + error);
          }}
          onLoad={() => {
            console.log('Dashboard loaded!');
            alert('Dashboard loaded successfully!');
          }}
        />
      </div>
      
      {/* Direct Iframe Test */}
      <div className="border rounded-lg mb-8">
        <div className="p-4 bg-gray-50 border-b">
          <h3 className="font-bold">Direct Iframe Test</h3>
          <p className="text-sm text-gray-600">Using a hardcoded embed URL for comparison</p>
        </div>
        <iframe
          src="https://us-east-1.quicksight.aws.amazon.com/embed/93fe81dc4e8c477bbd987c5eac902a43/dashboards/69aad539-a2da-4028-999a-472c19ff8348?code=AYABeMxlTRmCC20rZds3WUcLjxQAAAABAAdhd3Mta21zAEthcm46YXdzOmttczp1cy1lYXN0LTE6MjU5NDgwNDYyMTMyOmtleS81NGYwMjdiYy03MDJhLTQxY2YtYmViNS0xNDViOTExNzFkYzMAuAECAQB4g1oL4hdUJZc1aKfcGo-VQb_jBEsh0RowAd9MxoJqXpEBViOGYxF8ey9wujj9s8RbYwAAAH4wfAYJKoZIhvcNAQcGoG8wbQIBADBoBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDNsqav2Jt62aeWLg6wIBEIA7wGMDTLxX04GxaN1ZohSi8-UQBJbfdC1QpWj2kvkpYpKhvwR6rgbbD6GuAABkGkd7yflrgEJYBBXpVuUCAAAAAAwAABAAAAAAAAAAAAAAAAAAAfW1fZM74JwgI-4B-DmyTP____8AAAABAAAAAAAAAAAAAAABAAAAm1T1_GSRfoA32tuC6WMuKSUjcPuBO7X-pyG28HqLVI2GeEWzet7UIO5Z79duVuBE8CYgsNJQ1mBA6w5j65t2nqAkoIOpN5C2LbzfXV4DsVW47puBzxbL9oGa_8QBrnI3U63ru0Hh7qkkdf-FPpjfgZKueA6JDJW-wiZLAQDmm5J9uBHeAIo4EzFuFRNwNKcaLtSXOocUw65y9Is6NpRP8IuVVllhvxF2duMKnQ%3D%3D&identityprovider=quicksight&isauthcode=true"
          width="100%"
          height="400px"
          frameBorder="0"
          title="Direct QuickSight Test"
          style={{ border: 'none' }}
        />
      </div>
      
      <div className="mt-4 p-4 bg-gray-100 rounded">
        <h3 className="font-bold">Debug Info:</h3>
        <p><strong>API Base URL:</strong> {config.apiBaseUrl}</p>
        <p><strong>Dashboard ID:</strong> 69aad539-a2da-4028-999a-472c19ff8348</p>
        <p><strong>Environment:</strong> {config.isDevelopment ? 'Development' : 'Production'}</p>
        <p className="text-sm text-gray-600 mt-2">Check browser console for detailed logs</p>
      </div>
    </div>
  );
}