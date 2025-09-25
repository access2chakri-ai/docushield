"use client";

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';


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
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([]);
  const [selectedDocumentName, setSelectedDocumentName] = useState<string>('');
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
    const documentId = searchParams.get('document');
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
          }))
        })
      }, 120000); // 2 minutes timeout for AI operations

      if (!response.ok) {
        throw new Error(`Chat failed: ${response.statusText}`);
      }

      const chatResult = await response.json();

      // Create assistant response message
      const assistantMessage: Message = {
        id: Date.now().toString() + '_result',
        type: 'assistant',
        content: chatResult.response || 'I apologize, but I couldn\'t generate a response. Please try rephrasing your question.',
        timestamp: new Date(),
        steps: {
          total_steps: 1,
          execution_time: chatResult.processing_time || 0,
          retrieval_results: chatResult.sources || [],
          llm_analysis: chatResult.agent_results || [],
          external_actions: {}
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
      {/* Floating chat elements */}
      <div className="floating-document top-20 left-10 text-6xl">💬</div>
      <div className="floating-document top-36 right-8 text-5xl">🤖</div>
      <div className="floating-document bottom-32 left-1/5 text-4xl">💡</div>
      <div className="floating-document bottom-20 right-1/4 text-5xl">🔍</div>
      
      {/* AI processing flow */}
      <div className="data-flow top-0 left-1/5" style={{animationDelay: '1s'}}></div>
      <div className="data-flow top-0 right-1/5" style={{animationDelay: '3s'}}></div>
      
      <div className="container mx-auto px-4 py-8 max-w-4xl relative z-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI Document Chat</h1>
            <p className="text-gray-600">
              {selectedDocument && selectedDocumentName
                ? `Chatting about: ${selectedDocumentName}` 
                : `Ask questions about your uploaded documents`}
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

        {/* Document Selector */}
        {availableDocuments.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-4 mb-6">
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-gray-700">
                📄 Select Document:
              </label>
              <select
                value={selectedDocument || ''}
                onChange={(e) => handleDocumentChange(e.target.value)}
                className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              >
                <option value="">All Documents (General Chat)</option>
                {availableDocuments.map((doc) => (
                  <option key={doc.contract_id} value={doc.contract_id}>
                    {doc.filename} ({new Date(doc.created_at).toLocaleDateString()})
                  </option>
                ))}
              </select>
              {selectedDocument && (
                <Link
                  href={`/search`}
                  className="px-3 py-2 text-sm bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200"
                >
                  🔍 Advanced Search
                </Link>
              )}
            </div>
          </div>
        )}

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
                placeholder="Ask a question about your documents..."
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
                {isLoading ? '⏳' : 'Send'}
              </button>
            </div>
            
            <div className="mt-2 text-sm text-gray-500">
              💡 Try: {selectedDocument 
                ? `"Summarize this document", "What are the high-risk clauses?", "What recommendations are made?"`
                : `"What documents do I have?", "Show me high-risk contracts", "Find liability clauses"`
              }
            </div>
          </div>
        </div>

        <div className="mt-6 bg-blue-50 rounded-lg p-4">
          <h3 className="font-semibold mb-2">🔄 Multi-Step Process</h3>
          <p className="text-sm text-gray-700">
            Each question triggers: Vector Search → Document Retrieval → LLM Analysis → External Enrichment → Final Synthesis
          </p>
        </div>
      </div>
    </div>
  );
}