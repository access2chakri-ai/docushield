"use client";

import { useState, useEffect } from 'react';
import { authenticatedFetch } from '@/utils/auth';

interface LLMUsageStats {
  summary: {
    total_calls: number;
    total_tokens: number;
    total_cost: number;
    user_filter: boolean;
    timeframe: string;
  };
  by_provider: Record<string, {
    calls: number;
    tokens: number;
    cost: number;
    avg_latency: number;
    success_rate: number;
    models_used: string[];
  }>;
  recent_calls: Array<{
    call_id: string;
    provider: string;
    model: string;
    call_type: string;
    tokens: number;
    cost: number;
    latency_ms: number;
    success: boolean;
    purpose: string;
    created_at: string;
  }>;
}

interface ClaudeUsageStatsProps {
  userId?: string;
}

export default function ClaudeUsageStats({ userId }: ClaudeUsageStatsProps) {
  const [usageStats, setUsageStats] = useState<LLMUsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUsageStats();
  }, [userId]);

  const fetchUsageStats = async () => {
    try {
      setLoading(true);
      const url = userId ? `/api/providers/usage?user_id=${userId}` : '/api/providers/usage';
      const response = await authenticatedFetch(`http://localhost:8000${url}`);
      
      if (response.ok) {
        const data = await response.json();
        setUsageStats(data);
        setError(null);
      } else {
        throw new Error('Failed to fetch usage statistics');
      }
    } catch (err) {
      console.error('Failed to fetch usage stats:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'anthropic': return '🤖';
      case 'openai': return '🧠';
      case 'gemini': return '💎';
      case 'groq': return '⚡';
      default: return '🔧';
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'anthropic': return 'bg-orange-100 text-orange-800';
      case 'openai': return 'bg-green-100 text-green-800';
      case 'gemini': return 'bg-blue-100 text-blue-800';
      case 'groq': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-6 rounded-xl shadow-md">
        <h3 className="text-lg font-semibold mb-2 text-red-600">⚠️ Usage Stats Error</h3>
        <p className="text-gray-600 text-sm">{error}</p>
        <button 
          onClick={fetchUsageStats}
          className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!usageStats) {
    return (
      <div className="bg-white p-6 rounded-xl shadow-md">
        <h3 className="text-lg font-semibold mb-2">📊 AI Usage Stats</h3>
        <p className="text-gray-600 text-sm">No usage data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">🤖 AI Usage Statistics</h3>
        <button 
          onClick={fetchUsageStats}
          className="text-blue-600 hover:text-blue-700 text-sm"
        >
          🔄 Refresh
        </button>
      </div>
      
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{usageStats.summary.total_calls}</div>
          <div className="text-xs text-gray-500">Total Calls</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{usageStats.summary.total_tokens.toLocaleString()}</div>
          <div className="text-xs text-gray-500">Tokens Used</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">${usageStats.summary.total_cost.toFixed(4)}</div>
          <div className="text-xs text-gray-500">Total Cost</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-orange-600">{Object.keys(usageStats.by_provider).length}</div>
          <div className="text-xs text-gray-500">Providers</div>
        </div>
      </div>

      {/* Provider Breakdown */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-900">By Provider:</h4>
        {Object.entries(usageStats.by_provider).map(([provider, stats]) => (
          <div key={provider} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <span className="text-xl">{getProviderIcon(provider)}</span>
              <div>
                <div className="font-medium capitalize">{provider}</div>
                <div className="text-xs text-gray-500">
                  {stats.models_used.join(', ')} • {(stats.success_rate * 100).toFixed(1)}% success
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-semibold">{stats.calls} calls</div>
              <div className="text-xs text-gray-500">
                {stats.tokens.toLocaleString()} tokens • ${stats.cost.toFixed(4)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Calls */}
      {usageStats.recent_calls.length > 0 && (
        <div className="mt-6">
          <h4 className="font-medium text-gray-900 mb-3">Recent API Calls:</h4>
          <div className="space-y-2">
            {usageStats.recent_calls.slice(0, 5).map((call) => (
              <div key={call.call_id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getProviderColor(call.provider)}`}>
                    {call.provider}
                  </span>
                  <span className="text-gray-600">{call.purpose}</span>
                  {!call.success && <span className="text-red-500">❌</span>}
                </div>
                <div className="text-right text-xs text-gray-500">
                  <div>{call.tokens} tokens • ${call.cost.toFixed(4)}</div>
                  <div>{call.latency_ms}ms</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        {usageStats.summary.timeframe} • {usageStats.summary.user_filter ? 'Your usage only' : 'All users'}
      </div>
    </div>
  );
}
