"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';
import DocumentTypeFilter from '@/app/components/DocumentTypeFilter';

interface SearchResult {
  document_id: string;
  title: string;
  document_type: string;
  content_snippet: string;
  relevance_score: number;
  match_type: string;
  highlights: string[];
  metadata: {
    risk_level?: string;
    max_amount?: number;
    clause_type?: string;
    created_at?: string;
    file_size?: number;
  };
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time_ms: number;
  search_type: string;
  applied_filters: Record<string, any>;
  suggestions: string[];
}

export default function AdvancedSearchPage() {
  const [user, setUser] = useState<User | null>(null);
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('hybrid');
  const [documentFilter, setDocumentFilter] = useState('all');
  const [selectedDocumentTypes, setSelectedDocumentTypes] = useState<string[]>([]);
  const [selectedIndustryTypes, setSelectedIndustryTypes] = useState<string[]>([]);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const router = useRouter();

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      loadSuggestions();
    }
  }, [router]);

  const loadSuggestions = async () => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/search/suggestions`);
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const performSearch = async () => {
    if (!query.trim() || isLoading) return;

    setIsLoading(true);

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/search/advanced`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query.trim(),
          search_type: searchType,
          document_filter: documentFilter,
          limit: 20,
          filters: {},
          document_types: selectedDocumentTypes.length > 0 ? selectedDocumentTypes : null,
          industry_types: selectedIndustryTypes.length > 0 ? selectedIndustryTypes : null
        })
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const searchData: SearchResponse = await response.json();
      setSearchResponse(searchData);
      setResults(searchData.results || []);

    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
      setSearchResponse({
        query,
        results: [],
        total_results: 0,
        search_time_ms: 0,
        search_type: searchType,
        applied_filters: {},
        suggestions: [`Search failed: ${error}. Please check your connection and try again.`]
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

  const getResultIcon = (documentType: string) => {
    switch (documentType.toLowerCase()) {
      case 'contract': return '📄';
      case 'invoice': return '🧾';
      case 'clause': return '📋';
      case 'policy': return '📑';
      default: return '📄';
    }
  };

  const getRiskColor = (riskLevel?: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatAmount = (amount?: number) => {
    if (!amount) return '';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  return (
    <div className="min-h-screen bg-search-pattern relative overflow-hidden">
      {/* Floating search elements */}
      <div className="floating-document top-24 left-12 text-6xl">🔍</div>
      <div className="floating-document top-40 right-10 text-5xl">📊</div>
      <div className="floating-document bottom-36 left-1/6 text-4xl">⚡</div>
      <div className="floating-document bottom-24 right-1/3 text-5xl">🎯</div>
      
      {/* Search processing flow */}
      <div className="data-flow top-0 left-1/4" style={{animationDelay: '0.5s'}}></div>
      <div className="data-flow top-0 right-1/6" style={{animationDelay: '2.5s'}}></div>
      
      <div className="container mx-auto px-4 py-8 max-w-6xl relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">🔍 Advanced Search</h1>
            <p className="text-gray-600">
              Intelligent document search with semantic understanding and complex queries
            </p>
            {user && (
              <p className="text-sm text-gray-500">Logged in as: {user.name}</p>
            )}
          </div>
          <div className="flex space-x-4">
            <Link
              href="/documents"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              📄 My Documents
            </Link>
            <Link
              href="/chat"
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              💬 AI Chat
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Home
            </Link>
          </div>
        </div>

        {/* Search Interface */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="space-y-4">
            {/* Search Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Query
              </label>
              <div className="flex space-x-4">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Try: 'Find contracts with auto-renewal clauses' or 'Show invoices above $50k missing PO reference'"
                  className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                />
                <button
                  onClick={performSearch}
                  disabled={isLoading || !query.trim()}
                  className={`px-6 py-3 rounded-lg font-medium ${
                    isLoading || !query.trim()
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  } text-white`}
                >
                  {isLoading ? '🔍 Searching...' : '🔍 Search'}
                </button>
              </div>
            </div>

            {/* Search Options */}
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search Type
                </label>
                <select
                  value={searchType}
                  onChange={(e) => setSearchType(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                >
                  <option value="hybrid">Hybrid (Semantic + Keywords)</option>
                  <option value="semantic">Semantic Search</option>
                  <option value="keyword">Keyword Search</option>
                  <option value="structured">Structured Query</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Document Filter
                </label>
                <select
                  value={documentFilter}
                  onChange={(e) => setDocumentFilter(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                >
                  <option value="all">All Documents</option>
                  <option value="contracts">Contracts Only</option>
                  <option value="invoices">Invoices Only</option>
                  <option value="policies">Policies Only</option>
                  <option value="high_risk">High Risk Only</option>
                  <option value="recent">Recent Documents</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Document Type Filter */}
        <div className="mb-8">
          <DocumentTypeFilter
            selectedDocumentTypes={selectedDocumentTypes}
            selectedIndustryTypes={selectedIndustryTypes}
            onDocumentTypesChange={setSelectedDocumentTypes}
            onIndustryTypesChange={setSelectedIndustryTypes}
            onClearFilters={() => {
              setSelectedDocumentTypes([]);
              setSelectedIndustryTypes([]);
            }}
          />
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="space-y-4">
            {/* Example Queries */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💡 Example Queries (click to try):
              </label>
              <div className="flex flex-wrap gap-2">
                {suggestions.slice(0, 5).map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => setQuery(suggestion)}
                    className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
                    disabled={isLoading}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Search Results */}
        {searchResponse && (
          <div className="bg-white rounded-lg shadow-lg">
            {/* Results Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Search Results for "{searchResponse.query}"
                  </h2>
                  <p className="text-sm text-gray-500">
                    {searchResponse.total_results} results found in {searchResponse.search_time_ms.toFixed(0)}ms
                    • Search type: {searchResponse.search_type}
                  </p>
                </div>
              </div>
            </div>

            {/* Results List */}
            <div className="divide-y divide-gray-200">
              {results.length > 0 ? (
                results.map((result, index) => (
                  <div key={`${result.document_id}-${index}`} className="p-6 hover:bg-gray-50">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0 text-2xl">
                        {getResultIcon(result.document_type)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-medium text-gray-900 truncate">
                            {result.title}
                          </h3>
                          <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                            {result.document_type}
                          </span>
                          <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">
                            {(result.relevance_score * 100).toFixed(0)}% match
                          </span>
                          {result.metadata.risk_level && (
                            <span className={`px-2 py-1 text-xs rounded-full ${getRiskColor(result.metadata.risk_level)}`}>
                              {result.metadata.risk_level} risk
                            </span>
                          )}
                        </div>
                        
                        <p className="text-gray-600 mb-3 line-clamp-3">
                          {result.content_snippet}
                        </p>
                        
                        {/* Highlights */}
                        {result.highlights.length > 0 && (
                          <div className="mb-3">
                            <div className="flex flex-wrap gap-2">
                              {result.highlights.map((highlight, i) => (
                                <span
                                  key={i}
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
                          {result.metadata.max_amount && (
                            <span>💰 {formatAmount(result.metadata.max_amount)}</span>
                          )}
                          {result.metadata.clause_type && (
                            <span>📋 {result.metadata.clause_type}</span>
                          )}
                          {result.metadata.created_at && (
                            <span>📅 {new Date(result.metadata.created_at).toLocaleDateString()}</span>
                          )}
                          <span>🔍 {result.match_type}</span>
                        </div>
                        
                        {/* Actions */}
                        <div className="mt-3 flex space-x-3">
                          <Link
                            href={`/chat?document=${result.document_id}`}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            💬 Chat about this document
                          </Link>
                          <Link
                            href={`/documents/${result.document_id}/analysis`}
                            className="text-green-600 hover:text-green-800 text-sm font-medium"
                          >
                            📊 View analysis
                          </Link>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-12 text-center">
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No results found</h3>
                  <p className="text-gray-500 mb-4">
                    Try adjusting your search query or using different keywords.
                  </p>
                  
                  {/* Suggestions */}
                  {searchResponse.suggestions.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700 mb-2">💡 Suggestions:</p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {searchResponse.suggestions.map((suggestion, i) => (
                          <button
                            key={i}
                            onClick={() => setQuery(suggestion)}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200"
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
          <h3 className="text-lg font-semibold text-blue-900 mb-3">🚀 Advanced Search Tips</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm text-blue-800">
            <div>
              <h4 className="font-medium mb-2">Natural Language Queries:</h4>
              <ul className="space-y-1 list-disc list-inside">
                <li>"Find contracts with auto-renewal clauses"</li>
                <li>"Show high risk liability agreements"</li>
                <li>"Invoices above $50k missing PO reference"</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Search Types:</h4>
              <ul className="space-y-1 list-disc list-inside">
                <li><strong>Hybrid:</strong> Combines semantic understanding with keywords</li>
                <li><strong>Semantic:</strong> Understands meaning and context</li>
                <li><strong>Keyword:</strong> Traditional text matching</li>
                <li><strong>Structured:</strong> Filters by document properties</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}