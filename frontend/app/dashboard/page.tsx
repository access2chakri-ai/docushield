"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';

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
  overview: {
    total_contracts: number;
    recent_alerts: number;
    processing_stats: Record<string, number>;
  };
  risk_distribution: Record<string, number>;
  provider_usage: Record<string, any>;
}

export default function RiskDashboard() {
  const [contracts, setContracts] = useState<ContractAnalysis[]>([]);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [selectedContract, setSelectedContract] = useState<ContractAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchDashboardData();
    // Mock contract data for demo
    fetchMockContracts();
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
    } finally {
      setLoading(false);
    }
  };

  const fetchMockContracts = () => {
    // Mock data for demonstration
    const mockContracts: ContractAnalysis[] = [
      {
        contract: {
          contract_id: '1',
          filename: 'vendor-agreement-acme.pdf',
          status: 'completed',
          created_at: '2024-01-15T10:30:00Z'
        },
        score: {
          overall_score: 25,
          risk_level: 'critical',
          category_scores: { legal: 20, financial: 30, operational: 25 }
        },
        findings: [
          {
            finding_id: 'f1',
            type: 'liability_risk',
            severity: 'critical',
            title: 'Unlimited Liability Clause',
            description: 'Contract contains unlimited liability exposure',
            confidence: 0.9
          },
          {
            finding_id: 'f2',
            type: 'termination_risk',
            severity: 'high',
            title: 'Immediate Termination Rights',
            description: 'Vendor can terminate without notice',
            confidence: 0.8
          }
        ],
        suggestions: [
          {
            suggestion_id: 's1',
            type: 'renegotiate',
            title: 'Negotiate Liability Cap',
            description: 'Add liability limitation clause',
            priority: 'urgent',
            status: 'open'
          }
        ],
        alerts: [
          {
            alert_id: 'a1',
            type: 'risk_detected',
            severity: 'critical',
            title: 'High Risk Contract Detected',
            status: 'sent',
            created_at: '2024-01-15T10:35:00Z'
          }
        ]
      },
      {
        contract: {
          contract_id: '2',
          filename: 'service-agreement-beta.pdf',
          status: 'completed',
          created_at: '2024-01-14T14:20:00Z'
        },
        score: {
          overall_score: 65,
          risk_level: 'medium',
          category_scores: { legal: 70, financial: 60, operational: 65 }
        },
        findings: [
          {
            finding_id: 'f3',
            type: 'auto_renewal',
            severity: 'medium',
            title: 'Auto-Renewal Clause',
            description: 'Contract auto-renews without explicit consent',
            confidence: 0.7
          }
        ],
        suggestions: [
          {
            suggestion_id: 's2',
            type: 'add_clause',
            title: 'Add Termination Notice',
            description: 'Include 30-day termination notice requirement',
            priority: 'medium',
            status: 'open'
          }
        ],
        alerts: []
      },
      {
        contract: {
          contract_id: '3',
          filename: 'partnership-agreement-gamma.pdf',
          status: 'completed',
          created_at: '2024-01-13T09:15:00Z'
        },
        score: {
          overall_score: 85,
          risk_level: 'low',
          category_scores: { legal: 90, financial: 80, operational: 85 }
        },
        findings: [],
        suggestions: [
          {
            suggestion_id: 's3',
            type: 'optimize',
            title: 'Review Payment Terms',
            description: 'Consider negotiating better payment terms',
            priority: 'low',
            status: 'open'
          }
        ],
        alerts: []
      }
    ];

    setContracts(mockContracts);
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
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Risk Dashboard</h1>
            <p className="text-gray-600">Monitor contract risks and compliance across your organization</p>
          </div>
          <Link
            href="/"
            className="text-blue-600 hover:text-blue-800 flex items-center"
          >
            ← Back to Home
          </Link>
        </div>

        {/* Summary Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">{contracts.length}</p>
                <p className="text-sm text-gray-600">Total Contracts</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-red-100 text-red-600">
                🚨
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {contracts.filter(c => c.score?.risk_level === 'critical').length}
                </p>
                <p className="text-sm text-gray-600">Critical Risk</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-orange-100 text-orange-600">
                🔴
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {contracts.filter(c => c.score?.risk_level === 'high').length}
                </p>
                <p className="text-sm text-gray-600">High Risk</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600">
                ✅
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {contracts.filter(c => c.score?.risk_level === 'low').length}
                </p>
                <p className="text-sm text-gray-600">Low Risk</p>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700">Filter by risk level:</span>
            {['all', 'critical', 'high', 'medium', 'low'].map((level) => (
              <button
                key={level}
                onClick={() => setFilter(level)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === level
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Contracts Grid */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Contract List */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">Contracts</h2>
            {filteredContracts.map((contract) => (
              <div
                key={contract.contract.contract_id}
                className={`bg-white rounded-lg shadow p-6 cursor-pointer transition-all hover:shadow-lg ${
                  selectedContract?.contract.contract_id === contract.contract.contract_id
                    ? 'ring-2 ring-blue-500'
                    : ''
                }`}
                onClick={() => setSelectedContract(contract)}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{contract.contract.filename}</h3>
                    <p className="text-sm text-gray-500">
                      {new Date(contract.contract.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  {contract.score && (
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getRiskColor(contract.score.risk_level)}`}>
                      {getSeverityIcon(contract.score.risk_level)} {contract.score.risk_level.toUpperCase()}
                    </span>
                  )}
                </div>

                {contract.score && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Overall Score</span>
                      <span className="text-sm font-bold text-gray-900">{contract.score.overall_score}/100</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          contract.score.overall_score >= 80
                            ? 'bg-green-500'
                            : contract.score.overall_score >= 60
                            ? 'bg-yellow-500'
                            : contract.score.overall_score >= 40
                            ? 'bg-orange-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${contract.score.overall_score}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>{contract.findings.length} findings</span>
                  <span>{contract.suggestions.length} suggestions</span>
                  <span>{contract.alerts.length} alerts</span>
                </div>
              </div>
            ))}
          </div>

          {/* Contract Details */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Contract Details</h2>
            {selectedContract ? (
              <div className="space-y-6">
                {/* Contract Info */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4">Contract Information</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Filename:</span>
                      <span className="font-medium">{selectedContract.contract.filename}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span className="font-medium capitalize">{selectedContract.contract.status}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Created:</span>
                      <span className="font-medium">
                        {new Date(selectedContract.contract.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Risk Score */}
                {selectedContract.score && (
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4">Risk Analysis</h3>
                    <div className="space-y-4">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-gray-900 mb-1">
                          {selectedContract.score.overall_score}/100
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(selectedContract.score.risk_level)}`}>
                          {selectedContract.score.risk_level.toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="space-y-3">
                        {Object.entries(selectedContract.score.category_scores).map(([category, score]) => (
                          <div key={category}>
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium text-gray-700 capitalize">{category}</span>
                              <span className="text-sm text-gray-900">{score}/100</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : score >= 40 ? 'bg-orange-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${score}%` }}
                              ></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Findings */}
                {selectedContract.findings.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4">Risk Findings</h3>
                    <div className="space-y-4">
                      {selectedContract.findings.map((finding) => (
                        <div key={finding.finding_id} className="border-l-4 border-red-400 pl-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center mb-1">
                                <span className="mr-2">{getSeverityIcon(finding.severity)}</span>
                                <h4 className="font-medium text-gray-900">{finding.title}</h4>
                              </div>
                              <p className="text-sm text-gray-600 mb-2">{finding.description}</p>
                              <span className="text-xs text-gray-500">
                                Confidence: {Math.round(finding.confidence * 100)}%
                              </span>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(finding.severity)}`}>
                              {finding.severity.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggestions */}
                {selectedContract.suggestions.length > 0 && (
                  <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
                    <div className="space-y-4">
                      {selectedContract.suggestions.map((suggestion) => (
                        <div key={suggestion.suggestion_id} className="border-l-4 border-blue-400 pl-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h4 className="font-medium text-gray-900 mb-1">{suggestion.title}</h4>
                              <p className="text-sm text-gray-600 mb-2">{suggestion.description}</p>
                              <span className="text-xs text-gray-500 capitalize">
                                Priority: {suggestion.priority}
                              </span>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              suggestion.status === 'open' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                            }`}>
                              {suggestion.status.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <div className="text-gray-400 mb-4">
                  <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                  </svg>
                </div>
                <p className="text-gray-500">Select a contract to view detailed analysis</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
