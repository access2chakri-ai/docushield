"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ClaudeUsageStats from '../components/ClaudeUsageStats';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '../../utils/auth';
import { config } from '../../utils/config';

interface ContractAnalysis {
  contract: {
    contract_id: string;
    filename: string;
    status: string;
    created_at: string;
  };
  score: {
    overall_score: number;
    risk_level: string;
    category_scores: Record<string, number>;
  } | null;
  findings: Array<{
    finding_id: string;
    type: string;
    severity: string;
    title: string;
    description: string;
    confidence: number;
  }>;
  suggestions: Array<{
    suggestion_id: string;
    type: string;
    title: string;
    description: string;
    priority: string;
    status: string;
  }>;
  alerts: Array<{
    alert_id: string;
    type: string;
    severity: string;
    title: string;
    status: string;
    created_at: string;
  }>;
}

interface DashboardData {
  user_id: string;
  summary: {
    total_contracts: number;
    processed_contracts: number;
    high_risk_contracts: number;
  };
  risk_distribution: Array<{
    risk_level: string;
    count: number;
  }>;
  recent_activity: Array<{
    contract_id: string;
    filename: string;
    status: string;
    created_at: string;
  }>;
  provider_usage: Record<string, any>;
}

export default function RiskDashboard() {
  const [contracts, setContracts] = useState<ContractAnalysis[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [selectedContract, setSelectedContract] = useState<ContractAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [user, setUser] = useState<{user_id: string; name: string; email: string} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    // Initialize user from localStorage
    const userData = localStorage.getItem('docushield_user');
    if (userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (error) {
        console.error('Failed to parse user data:', error);
      }
    }
    
    fetchDashboardData();
    fetchContractAnalysis();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setError(null);
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/analytics/dashboard`);
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
        setRetryCount(0); // Reset retry count on success
      } else {
        throw new Error(`Dashboard API returned ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      setError(`Failed to load dashboard data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchContractAnalysis = async () => {
    try {
      setError(null);
      // Get real contract analysis data from TiDB
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/analytics/contracts/risk-analysis`);
      
      if (response.ok) {
        const data = await response.json();
        
        // Transform backend data to match frontend interface
        const contractAnalyses: ContractAnalysis[] = await Promise.all(
          data.contracts.slice(0, 5).map(async (contract: any) => {
            // For each contract, fetch detailed analysis if available
            try {
              const analysisResponse = await authenticatedFetch(`${config.apiBaseUrl}/api/documents/${contract.contract_id}/analysis`);
              
              if (analysisResponse.ok) {
                const analysisData = await analysisResponse.json();
                return analysisData;
              }
            } catch (error) {
              console.error(`Failed to fetch analysis for ${contract.contract_id}:`, error);
            }
            
            // Fallback to basic contract info if detailed analysis fails
            return {
              contract: {
                contract_id: contract.contract_id,
                filename: contract.filename,
                status: contract.overall_score ? 'completed' : 'processing',
                created_at: new Date().toISOString()
              },
              score: contract.overall_score ? {
                overall_score: contract.overall_score,
                risk_level: contract.risk_level,
                category_scores: contract.category_scores || {}
              } : null,
              findings: [],
              suggestions: [],
              alerts: []
            };
          })
        );
        
        setContracts(contractAnalyses);
      } else {
        throw new Error(`Contract analysis API returned ${response.status}`);
      }
    } catch (error) {
      console.error('Failed to fetch contract analysis:', error);
      setError(`Failed to load contract analysis: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setContracts([]);
    }
  };

  const handleRetry = () => {
    setLoading(true);
    setRetryCount(prev => prev + 1);
    fetchDashboardData();
    fetchContractAnalysis();
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return '🚨';
      case 'high': return '🔴';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const filteredContracts = contracts.filter(contract => {
    if (filter === 'all') return true;
    return contract.score?.risk_level === filter;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dashboard-pattern relative overflow-hidden">
      {/* Floating analytics elements */}
      <div className="floating-document top-16 left-8 text-5xl">📊</div>
      <div className="floating-document top-32 right-16 text-4xl">⚠️</div>
      <div className="floating-document bottom-40 left-1/5 text-6xl">📈</div>
      <div className="floating-document bottom-24 right-1/4 text-5xl">🔍</div>
      
      {/* Data processing flow */}
      <div className="data-flow top-0 left-1/5" style={{animationDelay: '0.5s'}}></div>
      <div className="data-flow top-0 right-1/4" style={{animationDelay: '1.5s'}}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Risk Dashboard</h1>
            <p className="text-gray-600">Monitor contract risks and insights across your organization</p>
            {user && (
              <p className="text-sm text-gray-500">Welcome back, {user.name}</p>
            )}
          </div>
          <div className="flex space-x-4">
            <Link
              href="/upload"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              📤 Upload Document
            </Link>
            <Link
              href="/search"
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
            >
              🔍 Advanced Search
            </Link>
            <Link
              href="/chat"
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              💬 AI Chat
            </Link>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="text-red-400 mr-3">⚠️</div>
                <div>
                  <h3 className="text-sm font-medium text-red-800">Dashboard Error</h3>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
              <button
                onClick={handleRetry}
                className="bg-red-100 hover:bg-red-200 text-red-800 px-3 py-2 rounded text-sm font-medium"
                disabled={loading}
              >
                {loading ? '🔄 Retrying...' : '🔄 Retry'}
              </button>
            </div>
          </div>
        )}

        {/* Dashboard Stats */}
        {dashboardData && (
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Contracts</h3>
              <p className="text-3xl font-bold text-blue-600">{dashboardData.summary?.total_contracts || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Processed</h3>
              <p className="text-3xl font-bold text-green-600">{dashboardData.summary?.processed_contracts || 0}</p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">High Risk</h3>
              <p className="text-3xl font-bold text-red-600">{dashboardData.summary?.high_risk_contracts || 0}</p>
            </div>
          </div>
        )}

        {/* Contract Analysis Grid */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Contract Analysis</h2>
            <div className="flex space-x-2">
              {['all', 'critical', 'high', 'medium', 'low'].map(level => (
                <button
                  key={level}
                  onClick={() => setFilter(level)}
                  className={`px-3 py-1 rounded text-sm font-medium ${
                    filter === level 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {level === 'all' ? 'All' : level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {filteredContracts.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <div className="text-gray-400 text-6xl mb-4">📄</div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No Contracts Found</h3>
              <p className="text-gray-600 mb-4">
                {filter === 'all' 
                  ? "Upload some documents to see contract analysis here."
                  : `No contracts with ${filter} risk level found.`}
              </p>
              <Link
                href="/upload"
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
              >
                Upload Your First Document
              </Link>
            </div>
          ) : (
            <div className="grid lg:grid-cols-2 gap-6">
              {filteredContracts.map((contract) => (
                <div key={contract.contract.contract_id} className="bg-white rounded-lg shadow p-6">
                  {/* Contract Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {contract.contract.filename}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {contract.contract.status} • {new Date(contract.contract.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {contract.score && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900 mb-1">
                          {contract.score.overall_score}/100
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(contract.score.risk_level)}`}>
                          {contract.score.risk_level.toUpperCase()}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Risk Summary */}
                  <div className="grid grid-cols-3 gap-4 mb-4 text-center">
                    <div>
                      <div className="text-lg font-semibold text-red-600">{contract.findings.length}</div>
                      <div className="text-xs text-gray-500">Findings</div>
                    </div>
                    <div>
                      <div className="text-lg font-semibold text-blue-600">{contract.suggestions.length}</div>
                      <div className="text-xs text-gray-500">Suggestions</div>
                    </div>
                    <div>
                      <div className="text-lg font-semibold text-orange-600">{contract.alerts.length}</div>
                      <div className="text-xs text-gray-500">Alerts</div>
                    </div>
                  </div>

                  {/* Key Findings */}
                  {contract.findings.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Key Findings:</h4>
                      <div className="space-y-2">
                        {contract.findings.slice(0, 2).map((finding) => (
                          <div key={finding.finding_id} className="flex items-start space-x-2">
                            <span className="text-sm">{getSeverityIcon(finding.severity)}</span>
                            <div className="flex-1">
                              <p className="text-sm font-medium text-gray-900">{finding.title}</p>
                              <p className="text-xs text-gray-600">
                                {(() => {
                                  try {
                                    // Try to parse JSON if it's a JSON string
                                    const parsed = JSON.parse(finding.description);
                                    if (parsed.clauses && Array.isArray(parsed.clauses)) {
                                      return `${parsed.clauses.length} clauses found`;
                                    }
                                    return finding.description.length > 30 
                                      ? `${finding.description.substring(0, 30)}...` 
                                      : finding.description;
                                  } catch {
                                    // If not JSON, just truncate to 30 characters
                                    return finding.description.length > 30 
                                      ? `${finding.description.substring(0, 30)}...` 
                                      : finding.description;
                                  }
                                })()}
                              </p>
                            </div>
                          </div>
                        ))}
                        {contract.findings.length > 2 && (
                          <p className="text-xs text-gray-500">
                            +{contract.findings.length - 2} more findings
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex space-x-2">
                    <Link
                      href={`/documents/${contract.contract.contract_id}/analysis`}
                      className="flex-1 bg-blue-600 text-white px-3 py-2 rounded text-sm text-center hover:bg-blue-700"
                    >
                      View Analysis
                    </Link>
                    <Link
                      href={`/chat?document=${contract.contract.contract_id}`}
                      className="flex-1 bg-purple-600 text-white px-3 py-2 rounded text-sm text-center hover:bg-purple-700"
                    >
                      Ask Questions
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Claude Usage Stats */}
        <div className="mt-8">
          <ClaudeUsageStats />
        </div>

        {/* Contract Details Modal */}
        {selectedContract && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-semibold">{selectedContract.contract.filename}</h3>
                  <button
                    onClick={() => setSelectedContract(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                
                {/* Contract details would go here */}
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium mb-2">Risk Score</h4>
                    {selectedContract.score && (
                      <div className="flex items-center space-x-4">
                        <div className="text-2xl font-bold">{selectedContract.score.overall_score}/100</div>
                        <span className={`px-2 py-1 rounded text-sm font-medium border ${getRiskColor(selectedContract.score.risk_level)}`}>
                          {selectedContract.score.risk_level.toUpperCase()} RISK
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <h4 className="font-medium mb-2">Findings ({selectedContract.findings.length})</h4>
                    <div className="space-y-2">
                      {selectedContract.findings.map((finding) => (
                        <div key={finding.finding_id} className="border-l-4 border-red-500 pl-3">
                          <div className="flex items-center space-x-2">
                            <span>{getSeverityIcon(finding.severity)}</span>
                            <span className="font-medium">{finding.title}</span>
                          </div>
                          <p className="text-sm text-gray-600">
                            {(() => {
                              try {
                                // Try to parse JSON if it's a JSON string
                                const parsed = JSON.parse(finding.description);
                                if (parsed.clauses && Array.isArray(parsed.clauses)) {
                                  return (
                                    <div className="space-y-2">
                                      <p>Found {parsed.clauses.length} clauses:</p>
                                      <ul className="list-disc list-inside space-y-1">
                                        {parsed.clauses.slice(0, 3).map((clause: any, idx: number) => (
                                          <li key={idx} className="text-xs">
                                            <strong>{clause.type}:</strong> {clause.matched_text} 
                                            {clause.context && ` (${clause.context.substring(0, 50)}...)`}
                                          </li>
                                        ))}
                                        {parsed.clauses.length > 3 && (
                                          <li className="text-xs text-gray-500">
                                            +{parsed.clauses.length - 3} more clauses
                                          </li>
                                        )}
                                      </ul>
                                    </div>
                                  );
                                }
                                return finding.description.length > 200 
                                  ? `${finding.description.substring(0, 200)}...` 
                                  : finding.description;
                              } catch {
                                // If not JSON, just truncate long descriptions
                                return finding.description.length > 200 
                                  ? `${finding.description.substring(0, 200)}...` 
                                  : finding.description;
                              }
                            })()}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}