// Example usage of the corrected QuickSightEmbedded component
import React from 'react';
import QuickSightEmbedded from '../components/QuickSightEmbedded';

// Example 1: Using with dashboardId (component will fetch embed URL)
export const QuickSightWithDashboardId = () => {
  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Dashboard with ID</h2>
      <QuickSightEmbedded
        dashboardId="your-dashboard-id"
        height="600px"
        width="100%"
      />
    </div>
  );
};

// Example 2: Using with direct embed URL
export const QuickSightWithEmbedUrl = () => {
  const embedUrl = "https://us-east-1.quicksight.aws.amazon.com/sn/embed/share/accounts/123456789012/dashboards/dashboard-id";
  
  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Dashboard with Embed URL</h2>
      <QuickSightEmbedded
        embedUrl={embedUrl}
        height="800px"
        width="100%"
      />
    </div>
  );
};

// Example 3: Using in a page with error handling
export const QuickSightPage = () => {
  const [dashboardId, setDashboardId] = React.useState<string>('');

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">QuickSight Analytics</h1>
      
      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dashboard ID
          </label>
          <input
            type="text"
            value={dashboardId}
            onChange={(e) => setDashboardId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
            placeholder="Enter dashboard ID"
          />
        </div>
        

      </div>

      {dashboardId && (
        <div className="border rounded-lg overflow-hidden">
          <QuickSightEmbedded
            dashboardId={dashboardId}
            height="700px"
            width="100%"
          />
        </div>
      )}
    </div>
  );
};