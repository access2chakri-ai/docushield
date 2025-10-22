"use client";

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '../../utils/auth';
import { config } from '../../utils/config';
import DocumentTypeFilter from '../components/DocumentTypeFilter';
import ProgressIndicator from '../components/ProgressIndicator';


interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  runId?: string;
  steps?: any;
}

interface RunResult {
  run_id: string;
  query: string;
  status: string;
  final_answer: string;
  current_step: number;
  total_steps: number;
  execution_time: number;
  retrieval_results: any[];
  llm_analysis: any;
  external_actions: any;
  steps: Array<{
    name: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    completed_at?: string;
  }>;
}

interface Document {
  contract_id: string;
  filename: string;
  status: string;
  created_at: string;
}

export default function ChatPage() {
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDataset] = useState('default');
  const [selectedDocumentTypes, setSelectedDocumentTypes] = useState<string[]>([]);
  const [selectedIndustryTypes, setSelectedIndustryTypes] = useState<string[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([]);
  const [selectedDocumentName, setSelectedDocumentName] = useState<string>('');
  const [chatMode, setChatMode] = useState<'documents' | 'all_documents' | 'general'>('documents');
  const [searchAllDocuments, setSearchAllDocuments] = useState<boolean>(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      loadUserDocuments(currentUser.user_id);
    }

    // Check if a specific document was selected
    const documentId = searchParams?.get('document');
    if (documentId) {
      setSelectedDocument(documentId);
    }

    // Set initial welcome message
    const welcomeMessage = documentId 
      ? `Welcome! I'm ready to answer questions about your selected document. What would you like to know?`
      : `Welcome ${currentUser?.name || 'User'}! I'm your document analysis agent. Upload some documents first, then ask me questions about them. I'll use TiDB vector search, LLM analysis chains, and external APIs to provide comprehensive answers.`;

    setMessages([{
      id: '1',
      type: 'system',
      content: welcomeMessage,
      timestamp: new Date()
    }]);
  }, [router, searchParams]);

  const loadUserDocuments = async (userId: string) => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents`);
      
      if (response.ok) {
        const data = await response.json();
        const completedDocs = data.documents.filter((doc: Document) => doc.status === 'completed');
        setAvailableDocuments(completedDocs);
        
        // Set selected document name if we have one selected
        if (selectedDocument) {
          const selectedDoc = completedDocs.find((doc: Document) => doc.contract_id === selectedDocument);
          if (selectedDoc) {
            setSelectedDocumentName(selectedDoc.filename);
          }
        }
      } else {
        console.warn('Failed to load documents:', response.status);
        setAvailableDocuments([]);
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('timed out')) {
        console.warn('Load documents request timed out - backend may not be running');
      } else {
        console.error('Failed to load documents:', error);
      }
      setAvailableDocuments([]);
      
      // Show error message in chat if no documents could be loaded
      setMessages(prev => [...prev, {
        id: Date.now().toString() + '_doc_error',
        type: 'system',
        content: '⚠️ Could not load your documents. Please check if the backend is running.',
        timestamp: new Date()
      }]);
    }
  };

  const handleDocumentChange = (documentId: string) => {
    setSelectedDocument(documentId);
    const selectedDoc = availableDocuments.find(doc => doc.contract_id === documentId);
    if (selectedDoc) {
      setSelectedDocumentName(selectedDoc.filename);
      
      // Update URL
      const newUrl = documentId ? `/chat?document=${documentId}` : '/chat';
      window.history.pushState({}, '', newUrl);
      
      // Clear messages and show new welcome message
      const welcomeMessage = `Welcome! I'm ready to answer questions about "${selectedDoc.filename}". What would you like to know?`;
      setMessages([{
        id: '1',
        type: 'system',
        content: welcomeMessage,
        timestamp: new Date()
      }]);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      // Use extended timeout for AI chat operations
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: currentInput,
          document_id: selectedDocument,
          conversation_history: messages.slice(-5).map(msg => ({
            role: msg.type === 'user' ? 'user' : 'assistant',
            content: msg.content
          })),
          document_types: selectedDocumentTypes.length > 0 ? selectedDocumentTypes : null,
          industry_types: selectedIndustryTypes.length > 0 ? selectedIndustryTypes : null,
          chat_mode: chatMode,
          search_all_documents: searchAllDocuments
        })
      }, 120000); // 2 minutes timeout for AI operations

      if (!response.ok) {
        throw new Error(`Chat failed: ${response.statusText}`);
      }

      const chatResult = await response.json();

      // Determine if this was enhanced with external data
      const isEnhanced = chatResult.agent_results?.some((agent: any) => agent.enhanced_with_external) || false;
      const hasDocumentContext = !!selectedDocument;

      // Create assistant response message with enhanced information
      const assistantMessage: Message = {
        id: Date.now().toString() + '_result',
        type: 'assistant',
        content: chatResult.response || 'I apologize, but I couldn\'t generate a response. Please try rephrasing your question.',
        timestamp: new Date(),
        steps: {
          total_steps: chatResult.agent_results?.length || 1,
          execution_time: chatResult.processing_time || 0,
          retrieval_results: chatResult.sources || [],
          llm_analysis: chatResult.agent_results || [],
          external_actions: isEnhanced ? { external_data: true } : {},
          document_context: hasDocumentContext,
          enhanced_with_external: isEnhanced,
          confidence: chatResult.confidence || 0.0
        }
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      let errorMessage = '❌ Failed to process your question.';
      
      if (error instanceof Error) {
        if (error.message.includes('fetch') || error.message.includes('NetworkError')) {
          errorMessage = '❌ Cannot connect to backend server. Please ensure it is running';
        } else if (error.message.includes('timeout') || error.message.includes('AbortError')) {
          errorMessage = '❌ Request timed out. The backend may be overloaded or not responding.';
        } else {
          errorMessage = `❌ Error: ${error.message}`;
        }
      }
      
      setMessages(prev => [...prev, {
        id: Date.now().toString() + '_error',
        type: 'system',
        content: errorMessage,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-chat-pattern relative overflow-hidden">
      {/* AI Thinking Background Overlay */}
      {isLoading && <div className="ai-thinking-overlay"></div>}
      {/* Floating chat elements */}
      <div className="floating-document top-20 left-10 text-6xl">💬</div>
      <div className="floating-document top-36 right-8 text-5xl">🤖</div>
      <div className="floating-document bottom-32 left-1/5 text-4xl">💡</div>
      <div className="floating-document bottom-20 right-1/4 text-5xl">🔍</div>
      
      {/* AI processing flow */}
      <div className="data-flow top-0 left-1/5" style={{animationDelay: '1s'}}></div>
      <div className="data-flow top-0 right-1/5" style={{animationDelay: '3s'}}></div>

      {/* AI Processing Animation */}
      {isLoading && (
        <div className="loading-overlay">
          <div className="shimmer-effect shimmer-purple"></div>
        </div>
      )}
      
      <div className="container mx-auto px-4 py-8 max-w-4xl relative z-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              💬 Chat with Your Documents
            </h1>
            <p className="text-gray-600">
              {selectedDocument && selectedDocumentName
                ? `Having a conversation about: ${selectedDocumentName}` 
                : `Ask me anything about your documents - I'll find the answers for you`}
            </p>
            {user && (
              <p className="text-sm text-gray-500">Chatting as: {user.name}</p>
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
              href="/upload"
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              📤 Upload Docs
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Home
            </Link>
          </div>
        </div>

        {/* Chat Mode Selector */}
        <div className="bg-white rounded-lg shadow-lg p-4 mb-6">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                🎯 Chat Mode:
              </label>
              <div className="flex space-x-2">
                <button
                  onClick={() => {
                    setChatMode('documents');
                    setSearchAllDocuments(false);
                  }}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                    chatMode === 'documents'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  disabled={isLoading}
                >
                  📄 Document Mode
                </button>
                <button
                  onClick={() => {
                    setChatMode('all_documents');
                    setSearchAllDocuments(true);
                    setSelectedDocument(null);
                  }}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                    chatMode === 'all_documents'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  disabled={isLoading}
                >
                  📚 All Documents
                </button>
                <button
                  onClick={() => {
                    setChatMode('general');
                    setSearchAllDocuments(false);
                  }}
                  className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                    chatMode === 'general'
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  disabled={isLoading}
                >
                  🌐 General Mode
                </button>
              </div>
            </div>
            
            <div className="text-xs text-gray-600 bg-gray-50 p-3 rounded">
              {chatMode === 'documents' && (
                <span>📄 <strong>Single Document:</strong> Focus on one specific document. Pick one below to get started.</span>
              )}
              {chatMode === 'all_documents' && (
                <span>📚 <strong>All Documents:</strong> I'll search through everything you've uploaded to find answers.</span>
              )}
              {chatMode === 'general' && (
                <span>🌐 <strong>General Questions:</strong> Ask me about anything - current events, stock prices, general knowledge.</span>
              )}
            </div>
          </div>
        </div>

        {/* Document Selector - Only show in Document Mode */}
        {chatMode === 'documents' && availableDocuments.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-4 mb-6">
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">
                📄 Which document should we talk about?
              </label>
              <select
                value={selectedDocument || ''}
                onChange={(e) => handleDocumentChange(e.target.value)}
                className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                <option value="">Pick a document to chat about...</option>
                {availableDocuments.map((doc) => (
                  <option key={doc.contract_id} value={doc.contract_id}>
                    {doc.filename} ({new Date(doc.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
              {selectedDocument && (
                <Link
                  href={`/search`}
                  className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                  🔍 Search Instead
                </Link>
              )}
            </div>
          </div>
        )}

        {/* Document Type Filter */}
        <div className="mb-6">
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

        <div className="bg-white rounded-lg shadow-lg">
          {/* Chat Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.type === 'user'
                      ? 'bg-blue-600 text-white'
                      : message.type === 'system'
                      ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  
                  {/* Show step details for assistant messages */}
                  {message.steps && (
                    <div className="mt-3 pt-3 border-t border-gray-200 text-xs">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <strong>Steps:</strong> {message.steps.total_steps}
                        </div>
                        <div>
                          <strong>Time:</strong> {message.steps.execution_time?.toFixed(2)}s
                        </div>
                        <div>
                          <strong>Documents:</strong> {message.steps.retrieval_results?.length || 0}
                        </div>
                        <div>
                          <strong>APIs:</strong> {Object.keys(message.steps.external_actions || {}).length}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs opacity-75 mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Input Area */}
          <div className="border-t p-4">
            <div className="flex space-x-4">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="What would you like to know? Ask me anything about your documents..."
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows={2}
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className={`px-6 py-3 rounded-lg font-medium ${
                  isLoading || !input.trim()
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                } text-white`}
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Thinking...
                  </span>
                ) : (
                  <span className="flex items-center">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Ask
                  </span>
                )}
              </button>
            </div>
            
            <div className="mt-2 text-sm text-gray-500">
              💡 Try: {
                chatMode === 'documents' && selectedDocument
                  ? `"Summarize this document", "What are the high-risk clauses?", "What recommendations are made?"`
                  : chatMode === 'all_documents'
                  ? `"Show me all contracts with renewal clauses", "Which documents have the highest risk?", "Find all liability terms"`
                  : chatMode === 'general'
                  ? `"What is Tesla's stock price?", "Latest AI news", "Explain force majeure clause"`
                  : `"Select a document or choose a mode to get started"`
              }
            </div>
          </div>
        </div>

        {/* Progress Indicator */}
        <ProgressIndicator
          isVisible={isLoading}
          operation="chatting"
        />

        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <h3 className="font-semibold mb-2">🤖 How I Work</h3>
          <p className="text-sm text-gray-700">
            When you ask a question, I search through your documents, analyze the content, and give you a helpful answer with sources.
          </p>
        </div>
      </div>
    </div>
  );
}