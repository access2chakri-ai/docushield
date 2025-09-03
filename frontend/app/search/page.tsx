"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface User {
  user_id: string;
  email: string;
  name: string;
}

interface SearchResult {
  document_id: string;
  title: string;
  document_type: string;
  content_snippet: string;
  relevance_score: number;
  match_type: string;
  highlights: string[];
  metadata: any;
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
  search_type: string;
  applied_filters: any;
  suggestions: string[];
}

export default function AdvancedSearchPage() {
  const [user, setUser] = useState<User | null>(null);
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('hybrid');
  const [documentFilter, setDocumentFilter] = useState('all');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [documentStats, setDocumentStats] = useState<any>(null);
  const [exampleQueries] = useState([
    "Find contracts with auto-renewal clauses",
    "Show invoices above $50k missing PO reference",
    "High risk liability agreements",
    "Recent contract documents",
    "Termination clauses in service agreements"
  ]);
  
  const router = useRouter();

  useEffect(() => {
    // Check authentication
    const userData = localStorage.getItem('docushield_user');
    if (!userData) {
      router.push('/auth');
      return;
    }

    const currentUser: User = JSON.parse(userData);
    setUser(currentUser);
    
    // Load search suggestions
    loadSuggestions(currentUser.user_id);
  }, [router]);

  const loadSuggestions = async (userId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/search/suggestions?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions);
        setDocumentStats(data.document_stats);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const performSearch = async () => {
    if (!query.trim() || !user) return;

    setIsLoading(true);
    
    try {
      const response = await fetch(`http://localhost:8000/api/search/advanced?user_id=${user.user_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          search_type: searchType,
          document_filter: documentFilter,
          limit: 20
        })
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const searchResponse: SearchResponse = await response.json();
      setResults(searchResponse);

    } catch (error) {
      console.error('Search error:', error);
      setResults({
        query: query,
        results: [],
        total_results: 0,
        search_time_ms: 0,
        search_type: searchType,
        applied_filters: {},
        suggestions: ['Search failed. Please try again.']
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      performSearch();
    }
  };

  const handleExampleQuery = (exampleQuery: string) => {
    setQuery(exampleQuery);
    // Auto-detect search type based on query
    if (exampleQuery.toLowerCase().includes('contract')) {
      setDocumentFilter('contracts');
    } else if (exampleQuery.toLowerCase().includes('invoice')) {
      setDocumentFilter('invoices');
    } else if (exampleQuery.toLowerCase().includes('risk')) {
      setDocumentFilter('high_risk');
    }
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getDocumentTypeIcon = (docType: string) => {
    switch (docType?.toLowerCase()) {
      case 'contract': return '📄';
      case 'invoice': return '💰';
      case 'policy': return '📋';
      case 'clause': return '📝';
      default: return '📄';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <img 
              src="/docushield-logo-svg.svg" 
              alt="DocuShield Logo" 
              className="h-10 w-auto"
            />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Advanced Document Search</h1>
              <p className="text-gray-600 mt-2">
                Intelligent search with semantic understanding and risk analysis
              </p>
              {user && (
                <p className="text-sm text-gray-500">Logged in as: {user.name}</p>
              )}
            </div>
          </div>
          <div className="flex space-x-4">
            <Link
              href="/documents"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              📄 My Documents
            </Link>
            <Link
              href="/upload"
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              📤 Upload
            </Link>
            <Link
              href="/chat"
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
            >
              💬 Chat
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Home
            </Link>
          </div>
        </div>

        {/* Document Statistics */}
        {documentStats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-2xl font-bold text-blue-600">{documentStats.total_documents}</div>
              <div className="text-sm text-gray-600">Total Documents</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-2xl font-bold text-green-600">{documentStats.contracts}</div>
              <div className="text-sm text-gray-600">Contracts</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-2xl font-bold text-yellow-600">{documentStats.invoices}</div>
              <div className="text-sm text-gray-600">Invoices</div>
            </div>
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="text-2xl font-bold text-red-600">{documentStats.high_risk}</div>
              <div className="text-sm text-gray-600">High Risk</div>
            </div>
          </div>
        )}

        {/* Search Interface */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          {/* Search Bar */}
          <div className="flex space-x-4 mb-4">
            <div className="flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Try: 'Find contracts with auto-renewal clauses' or 'Show invoices above $50k missing PO reference'"
                className="w-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg"
                disabled={isLoading}
              />
            </div>
            <button
              onClick={performSearch}
              disabled={isLoading || !query.trim()}
              className={`px-8 py-4 rounded-lg font-medium text-lg ${
                isLoading || !query.trim()
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              } text-white`}
            >
              {isLoading ? '🔍 Searching...' : 'Search'}
            </button>
          </div>

          {/* Search Options */}
          <div className="flex space-x-6 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Search Type</label>
              <select
                value={searchType}
                onChange={(e) => setSearchType(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="hybrid">🔗 Hybrid (Semantic + Keyword)</option>
                <option value="semantic">🧠 Semantic (AI Understanding)</option>
                <option value="keyword">🔤 Keyword (Text Matching)</option>
                <option value="structured">📊 Structured (Pattern Matching)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Document Type</label>
              <select
                value={documentFilter}
                onChange={(e) => setDocumentFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">📄 All Documents</option>
                <option value="contracts">📄 Contracts</option>
                <option value="invoices">💰 Invoices</option>
                <option value="policies">📋 Policies</option>
                <option value="high_risk">⚠️ High Risk</option>
                <option value="recent">🕒 Recent</option>
              </select>
            </div>
          </div>

          {/* Example Queries */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">💡 Example Queries:</h3>
            <div className="flex flex-wrap gap-2">
              {exampleQueries.map((example, index) => (
                <button
                  key={index}
                  onClick={() => handleExampleQuery(example)}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-blue-100 hover:text-blue-700 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Search Results */}
        {results && (
          <div className="bg-white rounded-lg shadow-lg">
            {/* Results Header */}
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Search Results for "{results.query}"
                  </h2>
                  <p className="text-gray-600 mt-1">
                    {results.total_results} results found in {results.search_time_ms.toFixed(0)}ms 
                    using {results.search_type} search
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500">
                    Search Type: <span className="font-medium">{results.search_type}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Results List */}
            <div className="divide-y divide-gray-200">
              {results.results.length > 0 ? (
                results.results.map((result, index) => (
                  <div key={index} className="p-6 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className="text-2xl">{getDocumentTypeIcon(result.document_type)}</span>
                          <Link 
                            href={`/documents/${result.document_id}/analysis`}
                            className="text-lg font-medium text-blue-600 hover:text-blue-800"
                          >
                            {result.title}
                          </Link>
                          <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                            {result.document_type}
                          </span>
                          <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                            {result.match_type}
                          </span>
                        </div>
                        
                        <p className="text-gray-700 mb-3 leading-relaxed">
                          {result.content_snippet}
                        </p>
                        
                        {/* Highlights */}
                        {result.highlights.length > 0 && (
                          <div className="mb-3">
                            <div className="flex flex-wrap gap-2">
                              {result.highlights.map((highlight, idx) => (
                                <span 
                                  key={idx}
                                  className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded"
                                >
                                  {highlight}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Metadata */}
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <span>📊 Relevance: {(result.relevance_score * 100).toFixed(0)}%</span>
                          {result.metadata.risk_level && (
                            <span className={`px-2 py-1 rounded-full text-xs ${getRiskColor(result.metadata.risk_level)}`}>
                              Risk: {result.metadata.risk_level}
                            </span>
                          )}
                          {result.metadata.created_at && (
                            <span>📅 {new Date(result.metadata.created_at).toLocaleDateString()}</span>
                          )}
                          {result.metadata.max_amount && (
                            <span>💰 ${result.metadata.max_amount.toLocaleString()}</span>
                          )}
                        </div>
                      </div>
                      
                      <div className="ml-4">
                        <Link
                          href={`/documents/${result.document_id}/analysis`}
                          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                        >
                          View Details
                        </Link>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-12 text-center">
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-xl font-medium text-gray-900 mb-2">No results found</h3>
                  <p className="text-gray-600 mb-4">
                    Try adjusting your search terms or using different filters
                  </p>
                  
                  {/* Suggestions */}
                  {results.suggestions.length > 0 && (
                    <div className="mt-6">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">💡 Suggestions:</h4>
                      <div className="flex flex-wrap justify-center gap-2">
                        {results.suggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleExampleQuery(suggestion)}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-4">🎯 Advanced Search Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            <div>
              <h4 className="font-medium text-blue-800 mb-2">Natural Language Queries</h4>
              <ul className="space-y-1 text-blue-700">
                <li>• "Find contracts with auto-renewal clauses"</li>
                <li>• "Show invoices above $50k missing PO reference"</li>
                <li>• "High risk liability agreements"</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-blue-800 mb-2">Search Types</h4>
              <ul className="space-y-1 text-blue-700">
                <li>• <strong>Hybrid:</strong> Combines AI understanding with keyword matching</li>
                <li>• <strong>Semantic:</strong> AI-powered meaning-based search</li>
                <li>• <strong>Keyword:</strong> Traditional text matching</li>
                <li>• <strong>Structured:</strong> Pattern and rule-based search</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
