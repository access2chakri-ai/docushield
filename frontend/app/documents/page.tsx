"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, logout, authenticatedFetch, type User } from '../../utils/auth';
import { config } from '../../utils/config';
import LoadingSpinner from '../components/LoadingSpinner';

// User interface is now imported from utils/auth

interface Document {
  contract_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  file_hash: string;
  status: string;
  created_at: string;
  has_raw_bytes: boolean;
}

interface DocumentsResponse {
  documents: Document[];
  total: number;
}

export default function DocumentsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showUpload, setShowUpload] = useState(false);
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
      fetchDocuments();
    } else {
      // If no user data but authenticated, there might be an issue
      setError('User data not found. Please try logging in again.');
      setLoading(false);
    }
  }, [router]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents?limit=50`);
      
      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid, redirect to login
          router.push('/auth');
          return;
        }
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const data: DocumentsResponse = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Error fetching documents:', err);
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          setError('Request timed out. Please check if the backend is running');
        } else if (err.message.includes('fetch') || err.message.includes('NetworkError')) {
          setError('Cannot connect to server. Please ensure the backend is running');
        } else {
          setError(err.message);
        }
      } else {
        setError('Failed to load documents');
      }
      // Set empty documents array to show the page
      setDocuments([]);
    } finally {
      // Ensure loading is always set to false
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push('/auth');
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (mimeType: string): string => {
    if (mimeType.includes('pdf')) return '📄';
    if (mimeType.includes('word') || mimeType.includes('docx')) return '📝';
    if (mimeType.includes('text')) return '📋';
    if (mimeType.includes('image')) return '🖼️';
    return '📄';
  };

  const getStatusColor = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'processing': return 'bg-yellow-100 text-yellow-800';
      case 'uploaded': return 'bg-blue-100 text-blue-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'timeout': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusMessage = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'completed': return 'Analysis Complete';
      case 'processing': return 'Processing...';
      case 'uploaded': return 'Ready for Processing';
      case 'failed': return 'Processing Failed';
      case 'timeout': return 'Processing Timeout';
      default: return status;
    }
  };

  const viewDocument = (document: Document) => {
    setSelectedDocument(document);
    // In a real app, you might open a modal or navigate to a detailed view
    router.push(`/documents/${document.contract_id}/analysis`);
  };



  const deleteDocument = async (document: Document, force: boolean = false) => {
    if (!user) return;

    const isProcessing = document.status === 'processing';
    let confirmMessage = `Are you sure you want to delete "${document.filename}"? This action cannot be undone and will remove all associated analysis data.`;
    
    if (isProcessing && !force) {
      confirmMessage = `"${document.filename}" is currently processing. This will force stop processing and delete the document. Continue?`;
    }

    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      const url = isProcessing && !force 
        ? `${config.apiBaseUrl}/api/documents/${document.contract_id}?force=true`
        : `${config.apiBaseUrl}/api/documents/${document.contract_id}`;
        
      const response = await authenticatedFetch(url, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || 'Failed to delete document');
      }

      alert(`Document "${document.filename}" deleted successfully`);
      
      // Refresh documents list
      fetchDocuments();
    } catch (err) {
      alert(`Delete failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  if (loading) {
    return (
      <LoadingSpinner 
        message="Loading your documents..." 
        timeout={8000}
        onTimeout={() => {
          setError('Loading timed out. Please check if the backend server is running');
          setLoading(false);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating document elements */}
      <div className="floating-document top-20 left-12 text-6xl">📄</div>
      <div className="floating-document top-48 right-8 text-5xl">📝</div>
      <div className="floating-document bottom-32 left-1/3 text-4xl">📋</div>
      <div className="floating-document bottom-16 right-1/5 text-5xl">🗂️</div>
      
      {/* Document processing flow */}
      <div className="data-flow top-0 left-1/6" style={{animationDelay: '0s'}}></div>
      <div className="data-flow top-0 right-1/5" style={{animationDelay: '2s'}}></div>
      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">My Documents</h1>
            <p className="text-gray-600 mt-1">
              Welcome back, {user?.name}! Manage your uploaded documents.
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              href="/upload"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center"
            >
              📤 Upload Document
            </Link>
            <button
              onClick={handleLogout}
              className="text-gray-600 hover:text-gray-800 flex items-center"
            >
              🚪 Logout
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600">
                📄
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">{documents.length}</p>
                <p className="text-sm text-gray-600">Total Documents</p>
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
                  {documents.filter(d => d.status === 'completed').length}
                </p>
                <p className="text-sm text-gray-600">Processed</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-600">
                ⏳
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {documents.filter(d => d.status === 'processing' || d.status === 'uploaded').length}
                </p>
                <p className="text-sm text-gray-600">Pending</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 text-purple-600">
                💾
              </div>
              <div className="ml-4">
                <p className="text-2xl font-bold text-gray-900">
                  {formatFileSize(documents.reduce((total, doc) => total + doc.file_size, 0))}
                </p>
                <p className="text-sm text-gray-600">Total Size</p>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Documents List */}
        {documents.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-gray-400 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
            <p className="text-gray-500 mb-6">
              Upload your first document to get started with AI-powered analysis.
            </p>
            <Link
              href="/upload"
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 inline-flex items-center"
            >
              📤 Upload Your First Document
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Document Library</h2>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Document
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Uploaded
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((document) => (
                    <tr key={document.contract_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="text-2xl mr-3">{getFileIcon(document.mime_type)}</span>
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {document.filename}
                            </div>
                            <div className="text-sm text-gray-500">
                              {document.mime_type}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(document.status)}`}>
                          {getStatusMessage(document.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatFileSize(document.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(document.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <Link
                          href={`/documents/${document.contract_id}/viewer`}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          👁️ View
                        </Link>

                        <Link
                          href={`/chat?document=${document.contract_id}`}
                          className="text-purple-600 hover:text-purple-900"
                        >
                          💬 Chat
                        </Link>
                        <button
                          onClick={() => deleteDocument(document)}
                          className="text-red-600 hover:text-red-900"
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-8 grid md:grid-cols-3 gap-6">
          <Link
            href="/upload"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
          >
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-600 group-hover:bg-blue-200">
                📤
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">Upload Document</h3>
                <p className="text-sm text-gray-600">Add new documents for analysis</p>
              </div>
            </div>
          </Link>

          <Link
            href="/chat"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
          >
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 text-purple-600 group-hover:bg-purple-200">
                💬
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">AI Chat</h3>
                <p className="text-sm text-gray-600">Ask questions about your documents</p>
              </div>
            </div>
          </Link>

          <Link
            href="/dashboard"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
          >
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-600 group-hover:bg-green-200">
                📊
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-semibold text-gray-900">Analytics</h3>
                <p className="text-sm text-gray-600">View insights and risk analysis</p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
