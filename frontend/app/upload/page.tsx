"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';

interface UploadedDocument {
  contract_id: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed' | 'validation_failed';
  upload_time: string;
  processing_error?: string;
}

export default function UploadPage() {
  const [user, setUser] = useState<User | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocuments, setUploadedDocuments] = useState<UploadedDocument[]>([]);
  const [statusPolling, setStatusPolling] = useState<string[]>([]);
  const [retryingDocuments, setRetryingDocuments] = useState<string[]>([]);
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
      // Load recent uploads
      loadRecentUploads();
    }
  }, [router]);

  // Load recent uploads on page load
  const loadRecentUploads = async () => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents?limit=5`);
      
      if (response.ok) {
        const data = await response.json();
        const recentDocs: UploadedDocument[] = data.documents.map((doc: any) => ({
          contract_id: doc.contract_id,
          filename: doc.filename,
          status: doc.status,
          upload_time: doc.created_at,
          processing_error: doc.status === 'failed' ? 'Processing failed - click retry' : undefined
        }));
        
        setUploadedDocuments(recentDocs);
        
        // Start polling for any documents that are still processing
        const processingDocs = recentDocs
          .filter(doc => doc.status === 'processing')
          .map(doc => doc.contract_id);
        
        if (processingDocs.length > 0) {
          setStatusPolling(processingDocs);
        }
      } else {
        console.warn('Failed to load recent uploads:', response.status);
        setUploadedDocuments([]);
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('timed out')) {
        console.warn('Recent uploads request timed out - backend may not be running');
        setError(`Cannot connect to backend server. Please ensure it is running on ${config.apiBaseUrl}`);
      } else {
        console.error('Failed to load recent uploads:', error);
      }
      setUploadedDocuments([]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file on frontend first
      const maxSize = 50 * 1024 * 1024; // 50MB
      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword', 'text/plain', 'text/markdown'];
      const allowedExtensions = ['.pdf', '.docx', '.doc', '.txt', '.md'];
      
      // Check file size
      if (selectedFile.size > maxSize) {
        setError(`File too large. Maximum size is 50MB. Your file is ${(selectedFile.size / (1024 * 1024)).toFixed(1)}MB.`);
        return;
      }
      
      // Check file extension
      const fileExtension = '.' + selectedFile.name.split('.').pop()?.toLowerCase();
      if (!allowedExtensions.includes(fileExtension)) {
        setError(`Unsupported file type: ${fileExtension}. DocuShield supports PDF, Word, and Text documents for analysis.`);
        return;
      }
      
      // Check if file is too small
      if (selectedFile.size < 100) {
        setError('File appears to be empty or too small. Please select a document with actual content.');
        return;
      }
      
      setFile(selectedFile);
      setError(null);
      setUploadResult(null);
    }
  };

  // Poll document status
  const pollDocumentStatus = async (contractId: string) => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents/${contractId}/status`);
      if (response.ok) {
        const statusData = await response.json();
        
        setUploadedDocuments(prev => 
          prev.map(doc => 
            doc.contract_id === contractId 
              ? { 
                  ...doc, 
                  status: statusData.status,
                  processing_error: statusData.error_message 
                }
              : doc
          )
        );

        // Stop polling if completed or failed
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          setStatusPolling(prev => prev.filter(id => id !== contractId));
        }
      }
    } catch (error) {
      console.error('Failed to poll status:', error);
    }
  };

  // Status polling effect
  useEffect(() => {
    if (statusPolling.length === 0) return;

    const interval = setInterval(() => {
      statusPolling.forEach(contractId => {
        pollDocumentStatus(contractId);
      });
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [statusPolling]);

  // Retry processing for failed documents
  const retryProcessing = async (contractId: string) => {
    setRetryingDocuments(prev => [...prev, contractId]);
    
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents/retry-processing`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contract_id: contractId
        }),
      });

      if (response.ok) {
        // Update document status to processing and start polling
        setUploadedDocuments(prev => 
          prev.map(doc => 
            doc.contract_id === contractId 
              ? { ...doc, status: 'processing', processing_error: undefined }
              : doc
          )
        );
        
        // Start polling for this document
        setStatusPolling(prev => [...prev, contractId]);
        
        setUploadResult(`🔄 Retry started for document!`);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Retry failed' }));
        
        // Handle specific retry limit errors
        if (response.status === 429) {
          setError(`Retry limit reached: ${errorData.detail}`);
        } else if (response.status === 422) {
          setError(`Validation issue: ${errorData.detail}`);
        } else {
          setError(`Retry failed: ${errorData.detail}`);
        }
      }
    } catch (error) {
      setError('Failed to retry processing');
      console.error('Retry failed:', error);
    } finally {
      setRetryingDocuments(prev => prev.filter(id => id !== contractId));
    }
  };

  const handleUpload = async () => {
    if (!file || !user) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        
        // Handle validation errors with detailed information
        if (response.status === 422 && errorData.detail && typeof errorData.detail === 'object') {
          const validationError = errorData.detail;
          setError(
            `Document validation failed: ${validationError.reason}\n\n` +
            `Supported document types:\n${validationError.supported_types?.join('\n• ') || 'Business documents only'}\n\n` +
            `Confidence: ${(validationError.confidence * 100).toFixed(1)}%`
          );
          return;
        }
        
        throw new Error(`Upload failed: ${errorData.detail || response.statusText}`);
      }

      const result = await response.json();
      
      // Add to uploaded documents list
      const newDocument: UploadedDocument = {
        contract_id: result.contract_id,
        filename: file.name,
        status: 'processing',
        upload_time: new Date().toISOString()
      };
      
      setUploadedDocuments(prev => [newDocument, ...prev]);
      setStatusPolling(prev => [...prev, result.contract_id]);
      
      setUploadResult(`✅ Upload successful! Processing ${file.name}...`);
      setFile(null);
      
      // Reset file input
      const fileInput = document.getElementById('fileInput') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-upload-pattern relative overflow-hidden">
      {/* Floating upload elements */}
      <div className="floating-document top-24 left-8 text-6xl">📤</div>
      <div className="floating-document top-40 right-12 text-5xl">☁️</div>
      <div className="floating-document bottom-36 left-1/4 text-4xl">⚡</div>
      <div className="floating-document bottom-20 right-1/3 text-5xl">✅</div>
      
      {/* Upload processing flow */}
      <div className="data-flow top-0 left-1/3" style={{animationDelay: '0.5s'}}></div>
      <div className="data-flow top-0 right-1/4" style={{animationDelay: '2.5s'}}></div>
      
      <div className="container mx-auto px-4 py-8 max-w-2xl relative z-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Upload Documents</h1>
            <p className="text-gray-600 mt-2">
              {user ? `Welcome ${user.name}! Add documents to your knowledge base` : 'Add documents to your knowledge base'}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              href="/documents"
              className="text-blue-600 hover:text-blue-800"
            >
              📄 My Documents
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Back to Home
            </Link>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">📄 Document Upload</h2>
            <p className="text-gray-600 mb-4">
              Upload PDF, DOCX, or text files to create vector embeddings and enable intelligent search.
            </p>
          </div>

          <div className="space-y-6">
            {/* File Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Document
              </label>
              <input
                id="fileInput"
                type="file"
                accept=".pdf,.docx,.txt,.md"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              <p className="mt-1 text-sm text-gray-500">
                Supported formats: PDF, DOCX, TXT, MD
              </p>
            </div>

            {/* File Info */}
            {file && (
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-medium text-blue-900">Selected File:</h3>
                <p className="text-blue-700">📄 {file.name}</p>
                <p className="text-sm text-blue-600">Size: {(file.size / 1024).toFixed(1)} KB</p>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || !user || isUploading}
              className={`w-full py-3 px-4 rounded-lg font-medium ${
                !file || !user || isUploading
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              } text-white`}
            >
              {isUploading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </span>
              ) : (
                '📤 Upload & Index Document'
              )}
            </button>

            {/* Success Message */}
            {uploadResult && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">Upload Successful!</h3>
                    <p className="text-sm text-green-700 mt-1">{uploadResult}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">Upload Failed</h3>
                    <p className="text-sm text-red-700 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Real-time Processing Status */}
          {uploadedDocuments.length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="font-medium text-gray-900 mb-4">📄 Recent Uploads & Processing Status</h3>
              <div className="space-y-3">
                {uploadedDocuments.slice(0, 5).map((doc) => (
                  <div key={doc.contract_id} className="bg-gray-50 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{doc.filename}</p>
                        <p className="text-sm text-gray-500">
                          Uploaded {new Date(doc.upload_time).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        {doc.status === 'processing' && (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                              Processing<span className="processing-dots"></span>
                            </span>
                          </>
                        )}
                        {doc.status === 'completed' && (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                            ✅ Completed
                          </span>
                        )}
                        {doc.status === 'failed' && (
                          <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                            ❌ Failed
                          </span>
                        )}
                        {doc.status === 'uploaded' && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                            📤 Uploaded
                          </span>
                        )}
                      </div>
                    </div>
                    {doc.status === 'failed' && doc.processing_error && (
                      <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                        <strong>Error:</strong> {doc.processing_error}
                        <div className="mt-2 flex items-center space-x-2">
                          <button 
                            onClick={() => retryProcessing(doc.contract_id)}
                            disabled={retryingDocuments.includes(doc.contract_id)}
                            className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                          >
                            {retryingDocuments.includes(doc.contract_id) ? 'Retrying...' : '🔄 Retry Processing'}
                          </button>
                          <span className="text-xs text-gray-500">
                            No need to upload again - we'll reprocess the same file
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          ⚠️ Limited to 3 retry attempts with 5-minute cooldown between retries
                        </div>
                      </div>
                    )}
                    
                    {doc.status === 'validation_failed' && (
                      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-700">
                        <strong>Validation Failed:</strong> This document type is not supported for processing.
                        <div className="mt-1 text-xs">
                          📋 We only process: SaaS contracts, vendor agreements, invoices, procurement documents, service agreements
                        </div>
                      </div>
                    )}
                    {doc.status === 'completed' && (
                      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                        <div className="flex items-center space-x-2">
                          <span>✅</span>
                          <span>Document processed successfully! Ready for search and analysis.</span>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          Processing complete - no further action needed
                        </div>
                      </div>
                    )}
                    {doc.status === 'processing' && (
                      <div className="mt-2 text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <span>🔄</span>
                          <span>Extracting text and creating embeddings...</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Next Steps */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <h3 className="font-medium text-gray-900 mb-3">What happens next?</h3>
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">1</span>
                <span>Document text is extracted and processed</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">2</span>
                <span>Vector embeddings are created using OpenAI</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">3</span>
                <span>Document is stored in TiDB with vector search capability</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">4</span>
                <span>Ready for intelligent Q&A and analysis!</span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          {uploadResult && (
            <div className="mt-6 flex space-x-4">
              <Link
                href="/documents"
                className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
              >
                📄 View My Documents
              </Link>
              <Link
                href="/chat"
                className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700"
              >
                💬 Start Asking Questions
              </Link>
              <button
                onClick={() => {
                  setUploadResult(null);
                  setError(null);
                }}
                className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700"
              >
                📄 Upload Another Document
              </button>
            </div>
          )}
        </div>

        {/* Tips */}
        <div className="mt-8 bg-yellow-50 rounded-lg p-6">
          <h3 className="font-semibold text-yellow-800 mb-2">💡 Tips for Best Results</h3>
          <ul className="text-sm text-yellow-700 space-y-1">
            <li>• Upload documents with clear, well-structured content</li>
            <li>• PDFs with text (not just images) work best</li>
            <li>• Larger documents provide more context for analysis</li>
            <li>• Upload multiple related documents for comprehensive answers</li>
          </ul>
        </div>
      </div>
    </div>
  );
}