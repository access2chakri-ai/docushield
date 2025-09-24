"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { config } from '../utils/config';

interface DashboardStats {
  overview: {
    total_contracts: number;
    recent_alerts: number;
    processing_stats: Record<string, number>;
  };
  risk_distribution: Record<string, number>;
  provider_usage: Record<string, any>;
}

interface ProviderStatus {
  providers: Record<string, {
    available: boolean;
    usage: any;
    models: string[];
  }>;
  settings: {
    default_provider: string;
    fallback_enabled: boolean;
    load_balancing: boolean;
  };
}

export default function Home() {
  const [dashboardData, setDashboardData] = useState<DashboardStats | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    fetchProviderStatus();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await fetch(`${config.apiBaseUrl}/api/analytics/dashboard`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      } else {
        console.warn('Dashboard API returned:', response.status);
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.warn('Dashboard API request timed out');
      } else {
        console.error('Failed to fetch dashboard data:', error);
      }
      // Set empty dashboard data to prevent infinite loading
      setDashboardData({
        overview: { total_contracts: 0, recent_alerts: 0, processing_stats: {} },
        risk_distribution: {},
        provider_usage: {}
      });
    }
  };

  const fetchProviderStatus = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
      
      const response = await fetch(`${config.apiBaseUrl}/health`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        // Handle the health endpoint response structure
        if (data.llm_providers) {
          setProviderStatus({
            providers: data.llm_providers,
            settings: {
              default_provider: 'openai',
              fallback_enabled: true,
              load_balancing: false
            }
          });
        } else {
          // Handle direct providers response
          setProviderStatus(data);
        }
      } else {
        console.warn('Health API returned:', response.status);
        // Set fallback status
        setProviderStatus({
          providers: {},
          settings: {
            default_provider: 'openai',
            fallback_enabled: true,
            load_balancing: false
          }
        });
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.warn('Health API request timed out');
      } else {
        console.error('Failed to fetch provider status:', error);
      }
      // Set fallback status to prevent infinite loading
      setProviderStatus({
        providers: {},
        settings: {
          default_provider: 'openai',
          fallback_enabled: true,
          load_balancing: false
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating document elements */}
      <div className="floating-document top-20 left-10 text-6xl">📄</div>
      <div className="floating-document top-40 right-20 text-5xl">📊</div>
      <div className="floating-document bottom-32 left-1/4 text-4xl">🔍</div>
      <div className="floating-document bottom-20 right-1/3 text-5xl">📋</div>
      
      {/* Subtle data flow lines */}
      <div className="data-flow top-0 left-1/4" style={{animationDelay: '0s'}}></div>
      <div className="data-flow top-0 right-1/3" style={{animationDelay: '1s'}}></div>
      <div className="data-flow top-0 left-2/3" style={{animationDelay: '2s'}}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="text-center max-w-6xl mx-auto mb-16">
          <div className="flex justify-end mb-4">
            <Link
              href="/auth"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200"
            >
              🔐 Login / Sign Up
            </Link>
          </div>
          
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <img 
              src="/docushield-logo-svg.svg" 
              alt="DocuShield Logo" 
              className="h-16 md:h-20 w-auto"
            />
          </div>
          
          {/* Hero Illustration */}
          <div className="flex justify-center mb-8 relative">
            <div className="relative">
              <img 
                src="/docushield-hero-illustration.svg" 
                alt="DocuShield Hero Illustration" 
                className="w-full max-w-4xl h-auto drop-shadow-lg"
              />
              {/* Floating elements for extra visual appeal */}
              <div className="absolute -top-4 -right-4 w-8 h-8 bg-blue-500 rounded-full opacity-20 animate-bounce"></div>
              <div className="absolute -bottom-2 -left-2 w-6 h-6 bg-purple-500 rounded-full opacity-30 animate-pulse"></div>
              <div className="absolute top-1/2 -right-8 w-4 h-4 bg-green-500 rounded-full opacity-25 animate-ping"></div>
            </div>
          </div>
          
          <p className="text-xl text-gray-600 mb-2 font-medium">
            AI-Powered Document Intelligence with Digital Twin Technology
          </p>
          <p className="text-sm text-gray-500">
            Powered by Multi-Cluster TiDB Serverless + LLM Factory (OpenAI, Anthropic, Gemini, Groq)
          </p>
        </div>

        {/* Navigation Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6 mb-12">
          <Link href="/documents" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-xl transition-all group-hover:scale-105 group-hover:-translate-y-1 duration-300 border border-gray-100">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900">My Documents</h3>
              <p className="text-gray-600 text-sm">View and manage your documents</p>
            </div>
          </Link>

          <Link href="/upload" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-xl transition-all group-hover:scale-105 group-hover:-translate-y-1 duration-300 border border-gray-100">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-200 transition-colors">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900">Upload Documents</h3>
              <p className="text-gray-600 text-sm">Upload contracts for AI analysis</p>
            </div>
          </Link>

          <Link href="/search" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-xl transition-all group-hover:scale-105 group-hover:-translate-y-1 duration-300 border border-gray-100">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-200 transition-colors">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900">Smart Search</h3>
              <p className="text-gray-600 text-sm">Hybrid semantic + keyword search</p>
            </div>
          </Link>

          <Link href="/digital-twin" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-xl transition-all group-hover:scale-105 group-hover:-translate-y-1 duration-300 border border-gray-100">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-orange-200 transition-colors">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900">Digital Twin</h3>
              <p className="text-gray-600 text-sm">AI-powered workflow modeling</p>
            </div>
          </Link>

          <Link href="/chat" className="group block">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-6 rounded-xl shadow-md hover:shadow-xl transition-all group-hover:scale-105 group-hover:-translate-y-1 duration-300 text-white">
              <div className="w-12 h-12 bg-white bg-opacity-20 rounded-lg flex items-center justify-center mb-4 group-hover:bg-opacity-30 transition-colors">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">AI Chat</h3>
              <p className="text-blue-100 text-sm">Chat with your documents</p>
            </div>
          </Link>
        </div>

        {/* Stats Section */}
        {!loading && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {/* Contract Stats */}
            <div className="bg-white p-6 rounded-xl shadow-md">
              <h3 className="text-lg font-semibold mb-4">📋 Contract Stats</h3>
              {dashboardData ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span>Total Contracts:</span>
                    <span className="font-semibold">{dashboardData.overview.total_contracts}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Recent Alerts:</span>
                    <span className="font-semibold text-red-600">{dashboardData.overview.recent_alerts}</span>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">No data available</p>
              )}
            </div>

            {/* Risk Distribution */}
            <div className="bg-white p-6 rounded-xl shadow-md">
              <h3 className="text-lg font-semibold mb-4">⚠️ Risk Distribution</h3>
              {dashboardData?.risk_distribution ? (
                <div className="space-y-2">
                  {Object.entries(dashboardData.risk_distribution).map(([level, count]) => (
                    <div key={level} className="flex justify-between items-center">
                      <span className={`px-2 py-1 rounded text-sm ${getRiskColor(level)}`}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No risk data available</p>
              )}
            </div>

            {/* Provider Status */}
            <div className="bg-white p-6 rounded-xl shadow-md">
              <h3 className="text-lg font-semibold mb-4">🤖 AI Providers</h3>
              {providerStatus && providerStatus.providers && Object.keys(providerStatus.providers).length > 0 ? (
                <div className="space-y-2">
                  {Object.entries(providerStatus.providers).map(([provider, status]) => (
                    <div key={provider} className="flex justify-between items-center">
                      <span className="capitalize">{provider}</span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        (status && typeof status === 'object' && status.available) ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                      }`}>
                        {(status && typeof status === 'object' && status.available) ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : loading ? (
                <p className="text-gray-500">Loading provider status...</p>
              ) : (
                <p className="text-gray-500">No providers available</p>
              )}
            </div>
          </div>
        )}

        {/* Features Section */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-12">
          <h2 className="text-3xl font-bold text-center mb-8">🚀 Platform Features</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-4xl mb-4">🏗️</div>
              <h3 className="text-xl font-semibold mb-3">Bronze → Silver → Gold</h3>
              <p className="text-gray-600">
                Multi-layer data architecture for enterprise document processing
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold mb-3">Hybrid Search</h3>
              <p className="text-gray-600">
                Vector similarity + full-text search powered by TiDB
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🧠</div>
              <h3 className="text-xl font-semibold mb-3">Multi-LLM Factory</h3>
              <p className="text-gray-600">
                OpenAI, Anthropic, Gemini, and Groq with intelligent routing
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-3">Risk Analysis</h3>
              <p className="text-gray-600">
                AI-powered contract risk assessment and scoring
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🔗</div>
              <h3 className="text-xl font-semibold mb-3">Multi-Cluster TiDB</h3>
              <p className="text-gray-600">
                Operational, Sandbox, and Analytics clusters for scalability
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">⚡</div>
              <h3 className="text-xl font-semibold mb-3">Real-time Processing</h3>
              <p className="text-gray-600">
                Async processing pipeline with live status updates
              </p>
            </div>
          </div>
        </div>

        {/* Demo Section */}
        <div className="text-center">
          <Link 
            href="/demo" 
            className="inline-block bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            🎯 Try Interactive Demo
          </Link>
        </div>
      </div>
    </div>
  );
}