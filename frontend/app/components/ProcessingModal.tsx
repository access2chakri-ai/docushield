"use client";

import { useState, useEffect } from 'react';

interface ProcessingModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileName?: string;
  stage: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  message?: string;
  canClose?: boolean;
}

export default function ProcessingModal({ 
  isOpen, 
  onClose, 
  fileName, 
  stage, 
  progress = 0,
  message,
  canClose = true
}: ProcessingModalProps) {
  const [dots, setDots] = useState('');

  useEffect(() => {
    if (stage === 'processing' || stage === 'uploading') {
      const interval = setInterval(() => {
        setDots(prev => prev.length >= 3 ? '' : prev + '.');
      }, 500);
      return () => clearInterval(interval);
    }
  }, [stage]);

  if (!isOpen) return null;

  const getStageInfo = () => {
    switch (stage) {
      case 'uploading':
        return {
          icon: '📤',
          title: 'Uploading Document',
          description: `Uploading ${fileName || 'your document'}${dots}`,
          color: 'blue'
        };
      case 'processing':
        return {
          icon: '🔄',
          title: 'Finding Valuable Insights',
          description: `We're processing your document and discovering important information${dots}`,
          color: 'purple'
        };
      case 'completed':
        return {
          icon: '✅',
          title: 'Processing Complete!',
          description: 'Your document has been successfully processed and is ready for analysis.',
          color: 'green'
        };
      case 'error':
        return {
          icon: '❌',
          title: 'Processing Failed',
          description: message || 'Something went wrong while processing your document.',
          color: 'red'
        };
      default:
        return {
          icon: '📄',
          title: 'Processing',
          description: 'Please wait...',
          color: 'gray'
        };
    }
  };

  const stageInfo = getStageInfo();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 z-50 pointer-events-none">
      <div className="fixed bottom-4 right-4 bg-white rounded-lg p-6 max-w-sm w-80 shadow-2xl modal-content pointer-events-auto">
        <div className="text-center">
          <div className="text-6xl mb-4">{stageInfo.icon}</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{stageInfo.title}</h2>
          <p className="text-gray-600 mb-6">{stageInfo.description}</p>
          
          {fileName && (
            <div className="bg-gray-50 rounded-lg p-3 mb-6">
              <p className="text-sm text-gray-700">
                <span className="font-medium">File:</span> {fileName}
              </p>
            </div>
          )}



          {stage === 'processing' && (
            <div className="mb-6">
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></div>
                  <span>Reading your document</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                  <span>Finding key information</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                  <span>Making it easy to search</span>
                </div>
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" style={{animationDelay: '0.6s'}}></div>
                  <span>Almost ready!</span>
                </div>
              </div>
            </div>
          )}

          {stage === 'completed' && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-green-800 text-sm">
                  🎉 Your document is now ready! You can search through it, ask questions, and get AI-powered insights.
                </p>
              </div>
              <button
                onClick={onClose}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 font-medium"
              >
                Great! Let's explore
              </button>
            </div>
          )}

          {stage === 'error' && (
            <div className="space-y-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-800 text-sm">{message}</p>
              </div>
              <button
                onClick={onClose}
                className="w-full bg-red-600 text-white py-3 px-4 rounded-lg hover:bg-red-700 font-medium"
              >
                Try Again
              </button>
            </div>
          )}

          {(stage === 'uploading' || stage === 'processing') && canClose && (
            <div className="text-center">
              <p className="text-sm text-gray-500 mb-4">
                We'll notify you when it's ready! Feel free to close and continue.
              </p>
              <div className="text-xs text-gray-400 mb-4">
                Processing usually takes 20-30 seconds
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Close & Continue
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}