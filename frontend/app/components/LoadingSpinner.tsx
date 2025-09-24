"use client";

import { useEffect, useState } from 'react';

interface LoadingSpinnerProps {
  message?: string;
  timeout?: number; // in milliseconds
  onTimeout?: () => void;
}

export default function LoadingSpinner({ 
  message = "Loading...", 
  timeout = 10000, // 10 seconds default
  onTimeout 
}: LoadingSpinnerProps) {
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);

  useEffect(() => {
    if (timeout > 0) {
      const timer = setTimeout(() => {
        setShowTimeoutWarning(true);
        if (onTimeout) {
          onTimeout();
        }
      }, timeout);

      return () => clearTimeout(timer);
    }
  }, [timeout, onTimeout]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600 mb-2">{message}</p>
        {showTimeoutWarning && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4 max-w-md">
            <p className="text-sm text-yellow-700">
              ⚠️ This is taking longer than expected. Please check if the backend server is running on http://localhost:8000
            </p>
          </div>
        )}
      </div>
    </div>
  );
}