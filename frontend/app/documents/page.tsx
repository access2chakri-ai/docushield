"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface User {
  user_id: string;
  email: string;
  name: string;
}

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
    const userData = localStorage.getItem('docushield_user');
    if (!userData) {
      router.push('/auth');
      return;
    }

    const currentUser: User = JSON.parse(userData);
    setUser(currentUser);
    fetchDocuments(currentUser.user_id);
  }, [router]);

  const fetchDocuments = async (userId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/documents?user_id=${userId}&limit=50`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const data: DocumentsResponse = await response.json();
      setDocuments(data.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('docushield_user');
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
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const viewDocument = (document: Document) => {
    setSelectedDocument(document);
    // In a real app, you might open a modal or navigate to a detailed view
    router.push(`/documents/${document.contract_id}/analysis`);
  };

  const processDocument = async (document: Document) => {
    if (!user) return;

    try {
      const response = await fetch('http://localhost:8000/api/documents/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contract_id: document.contract_id,
          user_id: user.user_id,
          trigger: 'manual'
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to process document');
      }

      const result = await response.json();
      alert(`Document processing started! Processing ID: ${result.processing_run_id}`);
      
      // Refresh documents list
      fetchDocuments(user.user_id);
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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
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
                          {document.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatFileSize(document.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(document.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <button
                          onClick={() => viewDocument(document)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          👁️ View
                        </button>
                        <button
                          onClick={() => processDocument(document)}
                          className="text-green-600 hover:text-green-900"
                          disabled={document.status === 'processing'}
                        >
                          ⚡ Process
                        </button>
                        <Link
                          href={`/chat?document=${document.contract_id}`}
                          className="text-purple-600 hover:text-purple-900"
                        >
                          💬 Chat
                        </Link>
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
