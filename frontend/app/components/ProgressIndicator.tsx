"use client";

import { useState, useEffect } from 'react';

interface ProgressIndicatorProps {
  isVisible: boolean;
  operation: 'searching' | 'chatting' | 'analyzing';
  message?: string;
  progress?: number;
}

export default function ProgressIndicator({ 
  isVisible, 
  operation, 
  message,
  progress = 0 
}: ProgressIndicatorProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [dots, setDots] = useState('');

  const getOperationSteps = () => {
    switch (operation) {
      case 'searching':
        return [
          'Searching through documents',
          'Finding relevant content',
          'Almost done!'
        ];
      case 'chatting':
        return [
          'Getting results for you',
          'Finding the best answer',
          'Preparing response',
          'Almost done!'
        ];
      case 'analyzing':
        return [
          'Reading your document',
          'Finding key insights',
          'Organizing findings',
          'Creating your report'
        ];
      default:
        return ['Working on your request'];
    }
  };

  const steps = getOperationSteps();

  useEffect(() => {
    if (!isVisible) return;

    // Animate dots
    const dotsInterval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);

    // Cycle through steps but stay at last step
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        const nextStep = prev + 1;
        // Stay at the last step ("Almost done!")
        return nextStep >= steps.length - 1 ? steps.length - 1 : nextStep;
      });
    }, 2000);

    return () => {
      clearInterval(dotsInterval);
      clearInterval(stepInterval);
    };
  }, [isVisible, steps.length]);

  if (!isVisible) return null;

  const getIcon = () => {
    switch (operation) {
      case 'searching': return '🔍';
      case 'chatting': return '💬';
      case 'analyzing': return '📊';
      default: return '⏳';
    }
  };

  const getColor = () => {
    switch (operation) {
      case 'searching': return 'blue';
      case 'chatting': return 'purple';
      case 'analyzing': return 'green';
      default: return 'gray';
    }
  };

  const color = getColor();

  const getBorderColor = () => {
    switch (operation) {
      case 'searching': return 'border-blue-400';
      case 'chatting': return 'border-purple-400';
      case 'analyzing': return 'border-green-400';
      default: return 'border-gray-400';
    }
  };

  const getDotColor = () => {
    switch (operation) {
      case 'searching': return 'bg-blue-700';
      case 'chatting': return 'bg-purple-700';
      case 'analyzing': return 'bg-green-700';
      default: return 'bg-gray-700';
    }
  };

  const getTextColor = () => {
    switch (operation) {
      case 'searching': return 'text-blue-900';
      case 'chatting': return 'text-purple-900';
      case 'analyzing': return 'text-green-900';
      default: return 'text-gray-900';
    }
  };

  const getBackgroundColor = () => {
    switch (operation) {
      case 'searching': return 'bg-blue-50';
      case 'chatting': return 'bg-purple-50';
      case 'analyzing': return 'bg-green-50';
      default: return 'bg-gray-50';
    }
  };

  const getProgressColor = () => {
    switch (operation) {
      case 'searching': return 'bg-blue-600';
      case 'chatting': return 'bg-purple-600';
      case 'analyzing': return 'bg-green-600';
      default: return 'bg-gray-600';
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <div className={`${getBackgroundColor()} border-2 ${getBorderColor()} rounded-lg shadow-xl p-4 max-w-sm`}>
        <div className="flex items-center space-x-3">
          <div className="text-3xl animate-pulse">{getIcon()}</div>
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 ${getDotColor()} rounded-full animate-bounce-dot`}></div>
              <div className={`w-3 h-3 ${getDotColor()} rounded-full animate-bounce-dot`}></div>
              <div className={`w-3 h-3 ${getDotColor()} rounded-full animate-bounce-dot`}></div>
            </div>
            <p className={`text-base font-semibold ${getTextColor()} mt-2`}>
              {message || steps[currentStep]}{dots}
            </p>
            {progress > 0 && (
              <div className="mt-2">
                <div className="w-full bg-gray-200 rounded-full h-1">
                  <div 
                    className={`h-1 rounded-full ${getProgressColor()} progress-bar`}
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            )}
            <p className="text-sm text-gray-700 mt-1 font-medium">Please wait...</p>
          </div>
        </div>
      </div>
    </div>
  );
}