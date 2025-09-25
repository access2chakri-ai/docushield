"use client";

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';

interface RiskHighlight {
  start_offset: number;
  end_offset: number;
  risk_level: 'high' | 'medium' | 'low' | 'critical';
  clause_type: string;
  title: string;
  description: string;
  confidence: number;
}

interface DocumentData {
  contract_id: string;
  filename: string;
  status: string;
  raw_text: string;
  highlights: RiskHighlight[];
  analysis_summary: {
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
    total_findings: number;
  };
}

export default function DocumentViewerPage() {
  const [user, setUser] = useState<User | null>(null);
  const [document, setDocument] = useState<DocumentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedHighlight, setSelectedHighlight] = useState<RiskHighlight | null>(null);
  const [viewMode, setViewMode] = useState<'text' | 'original'>('text');
  const [showRiskLevels, setShowRiskLevels] = useState({
    critical: true,
    high: true,
    medium: true,
    low: true
  });
  
  const router = useRouter();
  const params = useParams();
  const documentId = params.id as string;

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      loadDocument();
    }
  }, [router, documentId]);

  const loadDocument = async () => {
    try {
      setLoading(true);
      
      // Get document content and analysis
      const [documentResponse, analysisResponse] = await Promise.all([
        authenticatedFetch(`${config.apiBaseUrl}/api/documents/${documentId}/content`),
        authenticatedFetch(`${config.apiBaseUrl}/api/documents/${documentId}/analysis`)
      ]);

      if (!documentResponse.ok || !analysisResponse.ok) {
        throw new Error('Failed to load document or analysis');
      }

      const documentData = await documentResponse.json();
      const analysisData = await analysisResponse.json();

      // Combine data
      const combinedData: DocumentData = {
        contract_id: documentData.contract_id,
        filename: documentData.filename,
        status: documentData.status,
        raw_text: documentData.raw_text || '',
        highlights: analysisData.highlights || [],
        analysis_summary: {
          high_risk_count: analysisData.findings?.filter((f: any) => f.severity === 'high').length || 0,
          medium_risk_count: analysisData.findings?.filter((f: any) => f.severity === 'medium').length || 0,
          low_risk_count: analysisData.findings?.filter((f: any) => f.severity === 'low').length || 0,
          total_findings: analysisData.findings?.length || 0
        }
      };

      setDocument(combinedData);
    } catch (err) {
      console.error('Failed to load document:', err);
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'critical': return 'bg-red-200 border-red-400 text-red-900';
      case 'high': return 'bg-orange-200 border-orange-400 text-orange-900';
      case 'medium': return 'bg-yellow-200 border-yellow-400 text-yellow-900';
      case 'low': return 'bg-green-200 border-green-400 text-green-900';
      default: return 'bg-gray-200 border-gray-400 text-gray-900';
    }
  };

  const getRiskBadgeColor = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'critical': return 'bg-red-500 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-white';
      case 'low': return 'bg-green-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const renderHighlightedText = (text: string, highlights: RiskHighlight[]) => {
    if (!highlights || highlights.length === 0) {
      return <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed">{text}</div>;
    }

    // Filter highlights based on visibility settings
    const visibleHighlights = highlights.filter(h => showRiskLevels[h.risk_level]);

    // Sort highlights by start position
    const sortedHighlights = [...visibleHighlights].sort((a, b) => a.start_offset - b.start_offset);

    const elements = [];
    let lastOffset = 0;

    sortedHighlights.forEach((highlight, index) => {
      const { start_offset, end_offset, risk_level } = highlight;

      // Add text before highlight
      if (start_offset > lastOffset) {
        elements.push(
          <span key={`text-${index}`}>
            {text.substring(lastOffset, start_offset)}
          </span>
        );
      }

      // Add highlighted text
      const highlightedText = text.substring(start_offset, end_offset);
      elements.push(
        <span
          key={`highlight-${index}`}
          className={`${getRiskColor(risk_level)} px-1 py-0.5 rounded border cursor-pointer hover:shadow-md transition-shadow`}
          onClick={() => setSelectedHighlight(highlight)}
          title={`${risk_level.toUpperCase()} RISK: ${highlight.title}`}
        >
          {highlightedText}
        </span>
      );

      lastOffset = end_offset;
    });

    // Add remaining text
    if (lastOffset < text.length) {
      elements.push(
        <span key="text-end">
          {text.substring(lastOffset)}
        </span>
      );
    }

    return (
      <div className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
        {elements}
      </div>
    );
  };

  const renderOriginalDocument = () => {
    if (!document) return null;

    const originalDocUrl = `${config.apiBaseUrl}/api/documents/${documentId}/original`;
    
    // Check if it's a PDF
    if (document.filename.toLowerCase().endsWith('.pdf')) {
      return (
        <div className="relative w-full h-full">
          <iframe
            src={originalDocUrl}
            className="w-full h-screen border-0"
            title={`Original ${document.filename}`}
          />
          {/* Overlay highlights summary for PDFs */}
          <div className="absolute top-4 right-4 bg-white bg-opacity-95 p-3 rounded-lg shadow-lg max-w-xs max-h-96 overflow-y-auto">
            <h4 className="font-semibold text-sm mb-2">Risk Highlights Found:</h4>
            <div className="space-y-1 text-xs">
              {document.highlights.filter(h => showRiskLevels[h.risk_level]).map((highlight, index) => (
                <div 
                  key={index}
                  className={`p-2 rounded cursor-pointer ${getRiskColor(highlight.risk_level)}`}
                  onClick={() => setSelectedHighlight(highlight)}
                >
                  <div className="font-medium">{highlight.title}</div>
                  <div className="text-xs opacity-75">{highlight.clause_type}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    // For Word documents and other formats
    if (document.filename.toLowerCase().endsWith('.docx') || 
        document.filename.toLowerCase().endsWith('.doc')) {
      return (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">📝</div>
          <h3 className="text-lg font-semibold mb-2">Word Document Viewer</h3>
          <p className="text-gray-600 mb-4">
            Original format viewing for Word documents requires download.
          </p>
          <div className="space-y-4">
            <a
              href={originalDocUrl}
              download={document.filename}
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
            >
              📥 Download Original Document
            </a>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h4 className="font-semibold text-yellow-800 mb-2">📋 Highlights Summary</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {document.highlights.filter(h => showRiskLevels[h.risk_level]).map((highlight, index) => (
                  <div 
                    key={index}
                    className={`p-2 rounded cursor-pointer ${getRiskColor(highlight.risk_level)}`}
                    onClick={() => setSelectedHighlight(highlight)}
                  >
                    <div className="font-medium text-sm">{highlight.title}</div>
                    <div className="text-xs opacity-75">{highlight.clause_type}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // For text files and other formats
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">📄</div>
        <p className="text-gray-600 mb-4">
          Switch to Text View to see highlights for this document type.
        </p>
        <button
          onClick={() => setViewMode('text')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          Switch to Text View
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Document</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link
            href="/documents"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            ← Back to Documents
          </Link>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-400 text-6xl mb-4">📄</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Document Not Found</h1>
          <p className="text-gray-600 mb-4">The requested document could not be found.</p>
          <Link
            href="/documents"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            ← Back to Documents
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating viewer elements */}
      <div className="floating-document top-24 left-8 text-6xl">👁️</div>
      <div className="floating-document top-40 right-10 text-5xl">📖</div>
      <div className="floating-document bottom-36 left-1/5 text-4xl">🔍</div>
      <div className="floating-document bottom-20 right-1/4 text-5xl">📄</div>
      
      {/* Viewer flow lines */}
      <div className="data-flow top-0 left-1/4" style={{animationDelay: '0.5s'}}></div>
      <div className="data-flow top-0 right-1/5" style={{animationDelay: '2.5s'}}></div>
      
      <div className="container mx-auto px-4 py-8 max-w-7xl relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📄 Document Viewer</h1>
            <p className="text-gray-600">{document.filename}</p>
            {user && (
              <p className="text-sm text-gray-500">Logged in as: {user.name}</p>
            )}
          </div>
          <div className="flex space-x-4">
            <Link
              href={`/chat?document=${documentId}`}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              💬 Chat About This
            </Link>
            <Link
              href="/documents"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              📄 All Documents
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Home
            </Link>
          </div>
        </div>

        <div className="grid lg:grid-cols-4 gap-6">
          {/* Main Document Content */}
          <div className="lg:col-span-3">
            {/* Document Controls */}
            <div className="bg-white rounded-lg shadow-lg p-4 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Document Viewer</h2>
                <div className="flex items-center space-x-4">
                  {/* View Mode Toggle */}
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">View:</span>
                    <div className="flex bg-gray-100 rounded-lg p-1">
                      <button
                        onClick={() => setViewMode('text')}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                          viewMode === 'text' 
                            ? 'bg-blue-600 text-white' 
                            : 'text-gray-600 hover:text-gray-800'
                        }`}
                      >
                        📝 Text + Highlights
                      </button>
                      <button
                        onClick={() => setViewMode('original')}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                          viewMode === 'original' 
                            ? 'bg-blue-600 text-white' 
                            : 'text-gray-600 hover:text-gray-800'
                        }`}
                      >
                        📄 Original Format
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Level Controls - only show in text mode */}
              {viewMode === 'text' && (
                <div className="flex items-center justify-between mb-4 pt-4 border-t border-gray-200">
                  <h3 className="text-md font-medium text-gray-900">Risk Highlights</h3>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-600">Show:</span>
                    {Object.entries(showRiskLevels).map(([level, visible]) => (
                      <label key={level} className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={visible}
                          onChange={(e) => setShowRiskLevels(prev => ({
                            ...prev,
                            [level]: e.target.checked
                          }))}
                          className="rounded"
                        />
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskBadgeColor(level)}`}>
                          {level.toUpperCase()}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Summary */}
              <div className="flex items-center space-x-6 text-sm">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 bg-red-500 rounded"></span>
                  <span>Critical/High: {document.analysis_summary.high_risk_count}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 bg-yellow-500 rounded"></span>
                  <span>Medium: {document.analysis_summary.medium_risk_count}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 bg-green-500 rounded"></span>
                  <span>Low: {document.analysis_summary.low_risk_count}</span>
                </div>
                <div className="text-gray-600">
                  Total: {document.analysis_summary.total_findings} findings
                </div>
              </div>
            </div>

            {/* Document Content */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="border rounded-lg p-4 max-h-screen overflow-y-auto bg-gray-50">
                {viewMode === 'text' ? (
                  // Text view with highlights
                  document.raw_text ? (
                    renderHighlightedText(document.raw_text, document.highlights)
                  ) : (
                    <div className="text-center text-gray-500 py-12">
                      <div className="text-4xl mb-4">📄</div>
                      <p>Document content not available</p>
                      <p className="text-sm mt-2">The document may still be processing or the text extraction failed.</p>
                    </div>
                  )
                ) : (
                  // Original format view
                  renderOriginalDocument()
                )}
              </div>
            </div>
          </div>

          {/* Sidebar - Risk Details */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-4 sticky top-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Analysis</h3>
              
              {selectedHighlight ? (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Selected Risk</h4>
                  <div className={`p-3 rounded border ${getRiskColor(selectedHighlight.risk_level)} mb-3`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskBadgeColor(selectedHighlight.risk_level)}`}>
                        {selectedHighlight.risk_level.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-600">
                        {Math.round(selectedHighlight.confidence * 100)}% confidence
                      </span>
                    </div>
                    <h5 className="font-medium mb-1">{selectedHighlight.title}</h5>
                    <p className="text-sm">{selectedHighlight.description}</p>
                    <div className="mt-2 text-xs text-gray-600">
                      <strong>Type:</strong> {selectedHighlight.clause_type}
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedHighlight(null)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    ← Clear selection
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-600 mb-4">
                    Click on any highlighted text in the document to see detailed risk information.
                  </p>
                  
                  {/* Risk Legend */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-900">Risk Levels:</h4>
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="w-4 h-4 bg-red-500 rounded"></span>
                        <span className="text-sm">Critical - Immediate attention required</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="w-4 h-4 bg-orange-500 rounded"></span>
                        <span className="text-sm">High - Legal review recommended</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="w-4 h-4 bg-yellow-500 rounded"></span>
                        <span className="text-sm">Medium - Consider modifications</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="w-4 h-4 bg-green-500 rounded"></span>
                        <span className="text-sm">Low - Standard terms</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Quick Actions */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <h4 className="font-medium text-gray-900 mb-3">Quick Actions</h4>
                <div className="space-y-2">
                  <Link
                    href={`/chat?document=${documentId}`}
                    className="block w-full text-center bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
                  >
                    💬 Ask Questions
                  </Link>
                  <Link
                    href={`/documents/${documentId}/analysis`}
                    className="block w-full text-center bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700"
                  >
                    📊 Full Analysis
                  </Link>
                  <Link
                    href="/search"
                    className="block w-full text-center bg-purple-600 text-white px-3 py-2 rounded text-sm hover:bg-purple-700"
                  >
                    🔍 Search Similar
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

