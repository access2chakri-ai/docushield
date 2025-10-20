import { useEffect, useRef, useState } from 'react';
import { authenticatedFetch } from '../../utils/auth';
import { config } from '../../utils/config';

interface QuickSightEmbeddedProps {
  dashboardId?: string;
  embedUrl?: string;
  height?: string;
  width?: string;
  onError?: (error: string) => void;
  onLoad?: () => void;
}

const QuickSightEmbedded: React.FC<QuickSightEmbeddedProps> = ({
  dashboardId,
  embedUrl,
  height = '600px',
  width = '100%',
  onError,
  onLoad
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [finalUrl, setFinalUrl] = useState<string>('');

  useEffect(() => {
    const loadDashboard = async () => {
      console.log('🚀 QuickSight: Starting load process...');
      console.log('📋 Props:', { dashboardId, embedUrl });
      
      try {
        let urlToUse = embedUrl;
        
        // Get URL from backend if not provided
        if (!urlToUse && dashboardId) {
          console.log('🔗 Fetching embed URL from backend...');
          
          const response = await authenticatedFetch(`${config.apiBaseUrl}/api/embed-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dashboardId })
          });

          if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
          }

          const data = await response.json();
          console.log('✅ Backend response:', data);
          urlToUse = data.embedUrl;
        }

        if (!urlToUse) {
          throw new Error('No embed URL available');
        }

        console.log('🎯 Final URL:', urlToUse.substring(0, 100) + '...');
        setFinalUrl(urlToUse);
        setLoading(false);
        onLoad?.();

      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        console.error('❌ QuickSight error:', errorMsg);
        setError(errorMsg);
        setLoading(false);
        onError?.(errorMsg);
      }
    };

    if (dashboardId || embedUrl) {
      loadDashboard();
    }
  }, [dashboardId, embedUrl, onError, onLoad]);

  // Loading state
  if (loading) {
    return (
      <div style={{ 
        height, 
        width, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        background: '#f8f9fa'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #007bff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }}></div>
          <p style={{ color: '#6c757d', margin: 0 }}>Loading dashboard...</p>
        </div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{ 
        height, 
        width, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        border: '1px solid #f5c6cb',
        borderRadius: '8px',
        background: '#f8f9fa',
        color: '#dc3545'
      }}>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <h4>❌ Failed to load dashboard</h4>
          <p>{error}</p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              background: '#dc3545',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Success state - show iframe
  return (
    <div 
      ref={containerRef}
      style={{ 
        height, 
        width,
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        overflow: 'hidden'
      }}
    >
      <iframe
        src={finalUrl}
        width="100%"
        height="100%"
        frameBorder="0"
        style={{ border: 'none', display: 'block' }}
        title="QuickSight Dashboard"
        onLoad={() => console.log('✅ Iframe loaded successfully')}
        onError={(e) => console.error('❌ Iframe error:', e)}
      />
    </div>
  );
};

export default QuickSightEmbedded;