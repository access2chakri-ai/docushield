"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';

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
      const response = await fetch('/api/analytics/dashboard');
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  const fetchProviderStatus = async () => {
    try {
      const response = await fetch('/api/providers/status');
      if (response.ok) {
        const data = await response.json();
        setProviderStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch provider status:', error);
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center max-w-6xl mx-auto mb-12">
          <div className="flex justify-end mb-4">
            <Link
              href="/auth"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              🔐 Login / Sign Up
            </Link>
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            DocuShield
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Digital Twin Document Intelligence Platform
          </p>
          <p className="text-sm text-gray-500">
            Powered by Multi-Cluster TiDB Serverless + LLM Factory (OpenAI, Anthropic, Gemini, Groq)
          </p>
        </div>

        {/* Navigation Cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6 mb-12">
          <Link href="/documents" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow group-hover:scale-105 duration-200">
              <div className="text-blue-600 text-3xl mb-3">📚</div>
              <h3 className="text-xl font-semibold mb-2">My Documents</h3>
              <p className="text-gray-600">View and manage your documents</p>
            </div>
          </Link>

          <Link href="/upload" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow group-hover:scale-105 duration-200">
              <div className="text-blue-600 text-3xl mb-3">📄</div>
              <h3 className="text-xl font-semibold mb-2">Upload Documents</h3>
              <p className="text-gray-600">Upload contracts for AI analysis</p>
            </div>
          </Link>

          <Link href="/dashboard" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow group-hover:scale-105 duration-200">
              <div className="text-green-600 text-3xl mb-3">📊</div>
              <h3 className="text-xl font-semibold mb-2">Dashboard</h3>
              <p className="text-gray-600">View analytics and insights</p>
            </div>
          </Link>

          <Link href="/chat" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow group-hover:scale-105 duration-200">
              <div className="text-purple-600 text-3xl mb-3">💬</div>
              <h3 className="text-xl font-semibold mb-2">AI Chat</h3>
              <p className="text-gray-600">Chat with your documents</p>
            </div>
          </Link>

          <Link href="/digital-twin" className="group block">
            <div className="bg-white p-6 rounded-xl shadow-md hover:shadow-lg transition-shadow group-hover:scale-105 duration-200">
              <div className="text-orange-600 text-3xl mb-3">🤖</div>
              <h3 className="text-xl font-semibold mb-2">Digital Twin</h3>
              <p className="text-gray-600">AI-powered document analysis</p>
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
              {providerStatus ? (
                <div className="space-y-2">
                  {Object.entries(providerStatus.providers).map(([provider, status]) => (
                    <div key={provider} className="flex justify-between items-center">
                      <span className="capitalize">{provider}</span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        status.available ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                      }`}>
                        {status.available ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">Loading provider status...</p>
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