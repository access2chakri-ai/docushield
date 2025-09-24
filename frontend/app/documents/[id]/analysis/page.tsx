"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';



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

export default function DocumentAnalysisPage() {
  const [user, setUser] = useState<User | null>(null);
  const [analysis, setAnalysis] = useState<ContractAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
    }
  }, [router]);

  useEffect(() => {
    if (user && documentId) {
      fetchAnalysis(documentId);
    }
  }, [user, documentId]);

  const fetchAnalysis = async (contractId: string) => {
    if (!user) return;
    
    try {
      setLoading(true);
      const response = await authenticatedFetch(`http://localhost:8000/api/documents/${contractId}/analysis?user_id=${user.user_id}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Document not found or analysis not available');
        }
        throw new Error(`Failed to fetch analysis: ${response.statusText}`);
      }

      const data: ContractAnalysis = await response.json();
      
      // Defensive check to ensure we have the expected structure
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid analysis data received from server');
      }
      
      // Ensure contract object exists, create fallback if missing
      if (!data.contract) {
        data.contract = {
          contract_id: contractId,
          filename: 'Unknown Document',
          status: 'unknown',
          created_at: new Date().toISOString()
        };
      }
      
      // Ensure arrays exist, create empty arrays if missing
      if (!Array.isArray(data.findings)) data.findings = [];
      if (!Array.isArray(data.suggestions)) data.suggestions = [];
      if (!Array.isArray(data.alerts)) data.alerts = [];
      
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level: string): string => {
    switch (level.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string): string => {
    switch (severity.toLowerCase()) {
      case 'critical': return '🚨';
      case 'high': return '🔴';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const getPriorityIcon = (priority: string): string => {
    switch (priority.toLowerCase()) {
      case 'urgent': return '🚨';
      case 'high': return '🔴';
      case 'medium': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const triggerProcessing = async () => {
    if (!user) return;

    try {
      const response = await authenticatedFetch('http://localhost:8000/api/documents/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contract_id: documentId,
          user_id: user.user_id,
          trigger: 'manual'
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to process document');
      }

      const result = await response.json();
      alert(`Document processing started! Processing ID: ${result.processing_run_id}`);
      
      // Refresh analysis
      setTimeout(() => fetchAnalysis(documentId), 2000);
    } catch (err) {
      alert(`Processing failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">❌</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Analysis Not Available</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="space-x-4">
            <button
              onClick={() => triggerProcessing()}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
            >
              ⚡ Process Document
            </button>
            <Link
              href="/documents"
              className="bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700"
            >
              ← Back to Documents
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-400 text-6xl mb-4">📄</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">No Analysis Available</h1>
          <p className="text-gray-600 mb-6">This document hasn't been processed yet.</p>
          <button
            onClick={() => triggerProcessing()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            ⚡ Start Analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating analysis elements */}
      <div className="floating-document top-20 left-10 text-6xl">📊</div>
      <div className="floating-document top-36 right-8 text-5xl">🔍</div>
      <div className="floating-document bottom-32 left-1/4 text-4xl">⚠️</div>
      <div className="floating-document bottom-16 right-1/3 text-5xl">📋</div>
      
      {/* Analysis flow lines */}
      <div className="data-flow top-0 left-1/5" style={{animationDelay: '1s'}}></div>
      <div className="data-flow top-0 right-1/4" style={{animationDelay: '2s'}}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Document Analysis</h1>
            <p className="text-gray-600 mt-1">
              {analysis.contract?.filename || 'Unknown Document'}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              href={`/chat?document=${documentId}`}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center"
            >
              💬 Chat with Document
            </Link>
            <Link
              href="/documents"
              className="text-gray-600 hover:text-gray-800 flex items-center"
            >
              ← Back to Documents
            </Link>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Analysis */}
          <div className="lg:col-span-2 space-y-6">
            {/* Document Info */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Document Information</h2>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Filename</label>
                  <p className="text-sm text-gray-900">{analysis.contract?.filename || 'Unknown'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Status</label>
                  <p className="text-sm text-gray-900 capitalize">{analysis.contract?.status || 'Unknown'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Created</label>
                  <p className="text-sm text-gray-900">
                    {analysis.contract?.created_at ? new Date(analysis.contract.created_at).toLocaleDateString() : 'Unknown'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Contract ID</label>
                  <p className="text-sm text-gray-900 font-mono">{analysis.contract?.contract_id || 'Unknown'}</p>
                </div>
              </div>
            </div>

            {/* Risk Findings */}
            {analysis.findings.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Risk Findings</h2>
                <div className="space-y-4">
                  {analysis.findings.map((finding) => (
                    <div
                      key={finding.finding_id}
                      className={`border-l-4 pl-4 ${
                        finding.severity === 'critical' ? 'border-red-500' :
                        finding.severity === 'high' ? 'border-orange-500' :
                        finding.severity === 'medium' ? 'border-yellow-500' :
                        'border-green-500'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <span className="mr-2">{getSeverityIcon(finding.severity)}</span>
                            <h3 className="font-semibold text-gray-900">{finding.title}</h3>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{finding.description}</p>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span>Type: {finding.type}</span>
                            <span>Confidence: {Math.round(finding.confidence * 100)}%</span>
                          </div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(finding.severity)}`}>
                          {finding.severity.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {analysis.suggestions.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Recommendations</h2>
                <div className="space-y-4">
                  {analysis.suggestions.map((suggestion) => (
                    <div
                      key={suggestion.suggestion_id}
                      className="border-l-4 border-blue-500 pl-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <span className="mr-2">{getPriorityIcon(suggestion.priority)}</span>
                            <h3 className="font-semibold text-gray-900">{suggestion.title}</h3>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{suggestion.description}</p>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span>Type: {suggestion.type}</span>
                            <span>Priority: {suggestion.priority}</span>
                          </div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          suggestion.status === 'open' ? 'bg-yellow-100 text-yellow-800' : 
                          suggestion.status === 'accepted' ? 'bg-green-100 text-green-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {suggestion.status.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Alerts */}
            {analysis.alerts.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Alerts</h2>
                <div className="space-y-4">
                  {analysis.alerts.map((alert) => (
                    <div
                      key={alert.alert_id}
                      className={`border-l-4 pl-4 ${
                        alert.severity === 'critical' ? 'border-red-500' :
                        alert.severity === 'high' ? 'border-orange-500' :
                        alert.severity === 'medium' ? 'border-yellow-500' :
                        'border-green-500'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <span className="mr-2">{getSeverityIcon(alert.severity)}</span>
                            <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                          </div>
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span>Type: {alert.type}</span>
                            <span>Created: {new Date(alert.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getRiskColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Risk Score */}
            {analysis.score && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Overall Risk Score</h3>
                <div className="text-center mb-4">
                  <div className="text-4xl font-bold text-gray-900 mb-2">
                    {analysis.score.overall_score}/100
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(analysis.score.risk_level)}`}>
                    {analysis.score.risk_level.toUpperCase()} RISK
                  </span>
                </div>
                
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900">Category Breakdown:</h4>
                  {Object.entries(analysis.score.category_scores).map(([category, score]) => (
                    <div key={category}>
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700 capitalize">{category}</span>
                        <span className="text-sm text-gray-900">{score}/100</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            score >= 80 ? 'bg-green-500' : 
                            score >= 60 ? 'bg-yellow-500' : 
                            score >= 40 ? 'bg-orange-500' : 
                            'bg-red-500'
                          }`}
                          style={{ width: `${score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Stats */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Analysis Summary</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Risk Findings:</span>
                  <span className="font-semibold text-red-600">{analysis.findings.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Suggestions:</span>
                  <span className="font-semibold text-blue-600">{analysis.suggestions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Alerts:</span>
                  <span className="font-semibold text-orange-600">{analysis.alerts.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Critical Issues:</span>
                  <span className="font-semibold text-red-600">
                    {analysis.findings.filter(f => f.severity === 'critical').length}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={() => triggerProcessing()}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
                >
                  ⚡ Reprocess Document
                </button>
                <Link
                  href={`/chat?document=${documentId}`}
                  className="block w-full bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 text-sm text-center"
                >
                  💬 Ask Questions
                </Link>
                <Link
                  href="/documents"
                  className="block w-full bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 text-sm text-center"
                >
                  📄 View All Documents
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
