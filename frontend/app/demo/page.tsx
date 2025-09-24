"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface RunStep {
  step: number;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed';
  details?: any;
}

export default function DemoPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<RunStep[]>([
    {
      step: 1,
      title: "Document Ingestion & Vector Embedding",
      description: "Upload documents and create vector embeddings using OpenAI",
      status: 'pending'
    },
    {
      step: 2,
      title: "TiDB Vector Search",
      description: "Hybrid search combining vector similarity and full-text search",
      status: 'pending'
    },
    {
      step: 3,
      title: "Multi-step LLM Analysis",
      description: "Chain multiple LLM calls for summarization and analysis",
      status: 'pending'
    },
    {
      step: 4,
      title: "External API Integration",
      description: "Enrich results with external data sources",
      status: 'pending'
    },
    {
      step: 5,
      title: "Final Synthesis",
      description: "Combine all results into comprehensive answer",
      status: 'pending'
    }
  ]);

  const runDemo = async () => {
    setIsRunning(true);
    setCurrentStep(0);
    
    // Reset all steps
    setSteps(steps.map(step => ({ ...step, status: 'pending' })));
    
    // Simulate the multi-step process
    for (let i = 0; i < steps.length; i++) {
      setCurrentStep(i);
      
      // Mark current step as running
      setSteps(prev => prev.map((step, index) => 
        index === i ? { ...step, status: 'running' } : step
      ));
      
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 2000));
      
      // Mark current step as completed
      setSteps(prev => prev.map((step, index) => 
        index === i ? { ...step, status: 'completed' } : step
      ));
    }
    
    setIsRunning(false);
  };

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating demo elements */}
      <div className="floating-document top-20 left-8 text-6xl">🎯</div>
      <div className="floating-document top-40 right-10 text-5xl">⚡</div>
      <div className="floating-document bottom-32 left-1/4 text-4xl">🚀</div>
      <div className="floating-document bottom-16 right-1/5 text-5xl">✨</div>
      
      {/* Demo processing flow */}
      <div className="data-flow top-0 left-1/5" style={{animationDelay: '0s'}}></div>
      <div className="data-flow top-0 right-1/3" style={{animationDelay: '1.5s'}}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Multi-Step Agent Demo</h1>
              <p className="text-gray-600 mt-2">
                Watch how our agent processes documents through multiple steps
              </p>
            </div>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Back to Home
            </Link>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Workflow Visualization</h2>
              <button
                onClick={runDemo}
                disabled={isRunning}
                className={`px-6 py-2 rounded-lg font-medium ${
                  isRunning
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                } text-white`}
              >
                {isRunning ? 'Running Demo...' : 'Start Demo'}
              </button>
            </div>

            <div className="space-y-4">
              {steps.map((step, index) => (
                <div
                  key={step.step}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    step.status === 'completed'
                      ? 'border-green-200 bg-green-50'
                      : step.status === 'running'
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold ${
                        step.status === 'completed'
                          ? 'bg-green-500'
                          : step.status === 'running'
                          ? 'bg-blue-500 animate-pulse'
                          : 'bg-gray-400'
                      }`}
                    >
                      {step.status === 'completed' ? '✓' : step.step}
                    </div>
                    
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{step.title}</h3>
                      <p className="text-gray-600 text-sm">{step.description}</p>
                      
                      {step.status === 'running' && (
                        <div className="mt-2">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="text-sm">
                      {step.status === 'completed' && (
                        <span className="text-green-600 font-medium">✓ Completed</span>
                      )}
                      {step.status === 'running' && (
                        <span className="text-blue-600 font-medium">⏳ Processing...</span>
                      )}
                      {step.status === 'pending' && (
                        <span className="text-gray-400">⏸️ Pending</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">🎯 Demo Highlights</h3>
              <ul className="space-y-3 text-gray-600">
                <li className="flex items-start space-x-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span><strong>TiDB Vector Search:</strong> Semantic similarity search on document embeddings</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-500 mt-1">•</span>
                  <span><strong>Multi-step LLM Chain:</strong> Sequential reasoning and analysis</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-purple-500 mt-1">•</span>
                  <span><strong>External Integration:</strong> API calls for data enrichment</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-orange-500 mt-1">•</span>
                  <span><strong>Result Synthesis:</strong> Comprehensive answer generation</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">🔧 Technical Implementation</h3>
              <div className="space-y-3 text-sm text-gray-600">
                <div className="bg-gray-50 p-3 rounded">
                  <strong>Backend:</strong> FastAPI + TiDB + OpenAI
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <strong>Database:</strong> TiDB Serverless with Vector Search
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <strong>Frontend:</strong> Next.js + TypeScript
                </div>
                <div className="bg-gray-50 p-3 rounded">
                  <strong>AI:</strong> OpenAI GPT-4 + Embeddings
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 bg-blue-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-2">🚀 Try It Yourself!</h3>
            <p className="text-gray-700 mb-4">
              Ready to experience the full multi-step workflow? Upload your documents and ask questions!
            </p>
            <div className="flex space-x-4">
              <Link
                href="/upload"
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
              >
                Upload Documents
              </Link>
              <Link
                href="/chat"
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
              >
                Start Chatting
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
