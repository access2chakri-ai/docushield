"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '../../utils/auth';
import { config } from '../../utils/config';

import { useDocumentProcessing } from '../contexts/DocumentProcessingContext';

interface UploadedDocument {
  contract_id: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed' | 'validation_failed';
  upload_time: string;
  processing_error?: string;
  document_type?: string;
  industry_type?: string;
  document_category?: string;
}

export default function UploadPage() {
  const [user, setUser] = useState<User | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<string>('');
  const [industryType, setIndustryType] = useState<string>('');
  const [userDescription, setUserDescription] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocuments, setUploadedDocuments] = useState<UploadedDocument[]>([]);
  const [statusPolling, setStatusPolling] = useState<string[]>([]);
  const [retryingDocuments, setRetryingDocuments] = useState<string[]>([]);
  const [processingFileName, setProcessingFileName] = useState<string>('');
  const [showOptionalFields, setShowOptionalFields] = useState(false);

  const router = useRouter();
  
  // Use global notification system
  const { addNotification, startPolling } = useDocumentProcessing();

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
    setProcessingFileName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Add document classification data
      if (documentType) formData.append('document_type', documentType);
      if (industryType) formData.append('industry_type', industryType);
      if (userDescription) formData.append('user_description', userDescription);

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
        upload_time: new Date().toISOString(),
        document_type: result.document_type,
        industry_type: result.industry_type,
        document_category: result.document_category
      };

      setUploadedDocuments(prev => [newDocument, ...prev]);
      setStatusPolling(prev => [...prev, result.contract_id]);

      // Start global polling for this document
      startPolling(result.contract_id, file.name);

      // Show upload success notification with detailed explanation
      addNotification({
        type: 'info',
        title: 'Document Processing Started',
        message: `${file.name} is being analyzed. We're reading every page, extracting key information, and making it searchable. You'll get notified when it's ready!`,
        duration: 11000, // Increased by 3 seconds (8000 + 3000)
        category: 'upload'
      });

      setUploadResult(`✅ Upload successful! Processing ${file.name}...`);
      setFile(null);
      setDocumentType('');
      setIndustryType('');
      setUserDescription('');

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
      <div className="data-flow top-0 left-1/3" style={{ animationDelay: '0.5s' }}></div>
      <div className="data-flow top-0 right-1/4" style={{ animationDelay: '2.5s' }}></div>

      {/* Upload Processing Animation */}
      {isUploading && (
        <div className="loading-overlay">
          <div className="shimmer-effect shimmer-blue"></div>
        </div>
      )}

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
          {/* Header Section */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center mb-4">
              <div className="bg-blue-100 p-3 rounded-full">
                <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Share Your Documents</h2>
            <p className="text-gray-600 max-w-md mx-auto">
              Upload any document and we'll make it instantly searchable and ready for AI-powered analysis.
            </p>
          </div>

          <div className="max-w-lg mx-auto space-y-6">
            {/* File Upload Area */}
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors">
              <div className="space-y-4">
                <div className="mx-auto w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <label htmlFor="fileInput" className="cursor-pointer">
                    <span className="text-blue-600 font-medium hover:text-blue-500">Choose a file</span>
                    <span className="text-gray-500"> or drag and drop</span>
                  </label>
                  <input
                    id="fileInput"
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </div>
                <p className="text-xs text-gray-500">
                  PDF, Word, Text files supported • Max 50MB
                </p>
              </div>
            </div>

            {/* File Info Display */}
            {file && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-green-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-sm text-green-700">
                      {(file.size / 1024).toFixed(1)} KB • Ready to upload
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Optional Information */}
            <div className="space-y-4">
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setShowOptionalFields(!showOptionalFields)}
                  className="text-sm text-blue-600 hover:text-blue-500 font-medium"
                >
                  {showOptionalFields ? 'Hide' : 'Add'} optional details
                </button>
              </div>

              {showOptionalFields && (
                <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Document Type
                      </label>
                      <select
                        value={documentType}
                        onChange={(e) => setDocumentType(e.target.value)}
                        className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">Auto-detect</option>
                        <option value="Contract">Contract</option>
                        <option value="Agreement">Agreement</option>
                        <option value="Invoice">Invoice</option>
                        <option value="Proposal">Proposal</option>
                        <option value="Report">Report</option>
                        <option value="Policy">Policy</option>
                        <option value="Manual">Manual/Guide</option>
                        <option value="Specification">Technical Specification</option>
                        <option value="Legal Document">Legal Document</option>
                        <option value="Research Paper">Research Paper</option>
                        <option value="Whitepaper">Whitepaper</option>
                        <option value="Presentation">Presentation</option>
                        <option value="Memo">Memo</option>
                        <option value="Email">Email</option>
                        <option value="Letter">Letter</option>
                        <option value="Form">Form</option>
                        <option value="API Documentation">API Documentation</option>
                        <option value="User Guide">User Guide</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Industry
                      </label>
                      <select
                        value={industryType}
                        onChange={(e) => setIndustryType(e.target.value)}
                        className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">Select industry</option>
                        <option value="Technology/SaaS">Technology/SaaS</option>
                        <option value="Legal">Legal</option>
                        <option value="Financial Services">Financial Services</option>
                        <option value="Healthcare">Healthcare</option>
                        <option value="Real Estate">Real Estate</option>
                        <option value="Manufacturing">Manufacturing</option>
                        <option value="Retail">Retail</option>
                        <option value="Education">Education</option>
                        <option value="Government">Government</option>
                        <option value="Non-profit">Non-profit</option>
                        <option value="Consulting">Consulting</option>
                        <option value="Media">Media</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Description
                    </label>
                    <textarea
                      value={userDescription}
                      onChange={(e) => setUserDescription(e.target.value)}
                      placeholder="What's this document about? Any specific things to focus on?"
                      rows={2}
                      className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || !user || isUploading}
              className={`w-full py-4 px-6 rounded-lg font-semibold text-lg transition-all ${!file || !user || isUploading
                ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl'
                }`}
            >
              {isUploading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </span>
              ) : (
                <span className="flex items-center justify-center">
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload Document
                </span>
              )}
            </button>



            {/* Quick Info */}
            <div className="text-center">
              <p className="text-sm text-gray-500">
                ✨ We'll read your document and make it instantly searchable
              </p>
            </div>
          </div>

          {/* Success Message */}
          {uploadResult && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
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
                  <svg className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
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
                      {doc.document_type && (
                        <p className="text-xs text-gray-500">Type: {doc.document_type}</p>
                      )}
                      {doc.industry_type && (
                        <p className="text-xs text-gray-500">Industry: {doc.industry_type}</p>
                      )}
                      {doc.document_category && (
                        <p className="text-xs text-blue-600">Classified as: {doc.document_category}</p>
                      )}
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
          <h3 className="font-medium text-gray-900 mb-3">Why does processing take a moment?</h3>
          <div className="space-y-3 text-sm text-gray-600">
            <div className="flex items-start space-x-3">
              <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium mt-0.5">1</span>
              <div>
                <span className="font-medium text-gray-800">Reading every page</span>
                <p className="text-xs text-gray-500 mt-1">We carefully extract text from your document, preserving formatting and structure</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium mt-0.5">2</span>
              <div>
                <span className="font-medium text-gray-800">Understanding the content</span>
                <p className="text-xs text-gray-500 mt-1">AI analyzes the meaning and context of each section to enable smart search</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium mt-0.5">3</span>
              <div>
                <span className="font-medium text-gray-800">Making it searchable</span>
                <p className="text-xs text-gray-500 mt-1">Creating an intelligent index so you can find information instantly</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="w-6 h-6 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-xs font-medium mt-0.5">✓</span>
              <div>
                <span className="font-medium text-green-800">Ready for questions!</span>
                <p className="text-xs text-gray-500 mt-1">Ask anything about your document and get precise, contextual answers</p>
              </div>
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

      {/* What We Support */}
      <div className="mt-12 text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">We work with all your documents</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl mb-2">📄</div>
            <p className="text-sm font-medium text-green-800">Business Documents</p>
            <p className="text-xs text-green-600">Contracts, invoices, proposals</p>
          </div>
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl mb-2">📚</div>
            <p className="text-sm font-medium text-blue-800">Technical Docs</p>
            <p className="text-xs text-blue-600">Manuals, specifications, guides</p>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <div className="text-2xl mb-2">🔬</div>
            <p className="text-sm font-medium text-purple-800">Research</p>
            <p className="text-xs text-purple-600">Papers, studies, reports</p>
          </div>
        </div>
      </div>






    </div>
  );
}