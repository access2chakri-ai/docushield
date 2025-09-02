"use client";

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface User {
  user_id: string;
  email: string;
  name: string;
}

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  runId?: string;
  steps?: any;
}

interface RunResult {
  id: string;
  query: string;
  status: string;
  final_answer: string;
  total_steps: number;
  execution_time: number;
  retrieval_results: any[];
  llm_analysis: any;
  external_actions: any;
}

export default function ChatPage() {
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDataset] = useState('default');
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check authentication
    const userData = localStorage.getItem('docushield_user');
    if (!userData) {
      router.push('/auth');
      return;
    }

    const currentUser: User = JSON.parse(userData);
    setUser(currentUser);

    // Check if a specific document was selected
    const documentId = searchParams.get('document');
    if (documentId) {
      setSelectedDocument(documentId);
    }

    // Set initial welcome message
    const welcomeMessage = documentId 
      ? `Welcome! I'm ready to answer questions about your selected document. What would you like to know?`
      : `Welcome ${currentUser.name}! I'm your document analysis agent. Upload some documents first, then ask me questions about them. I'll use TiDB vector search, LLM analysis chains, and external APIs to provide comprehensive answers.`;

    setMessages([{
      id: '1',
      type: 'system',
      content: welcomeMessage,
      timestamp: new Date()
    }]);
  }, [router, searchParams]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Step 1: Start the analysis
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: input,
          dataset_id: selectedDataset,
          user_id: user?.user_id
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start analysis');
      }

      const { run_id } = await response.json();

      // Add processing message
      const processingMessage: Message = {
        id: Date.now().toString() + '_processing',
        type: 'system',
        content: '🤖 Running multi-step analysis...\n\n⏳ Step 1: Searching documents with TiDB vector search\n⏳ Step 2: Analyzing with LLM chain\n⏳ Step 3: Enriching with external APIs\n⏳ Step 4: Synthesizing final answer',
        timestamp: new Date(),
        runId: run_id
      };

      setMessages(prev => [...prev, processingMessage]);

      // Step 2: Poll for results
      let attempts = 0;
      const maxAttempts = 30;
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        const resultResponse = await fetch(`http://localhost:8000/api/runs/${run_id}`);
        
        if (resultResponse.ok) {
          const result: RunResult = await resultResponse.json();
          
          if (result.status === 'completed') {
            // Remove processing message
            setMessages(prev => prev.filter(msg => msg.runId !== run_id));
            
            // Add detailed result
            const resultMessage: Message = {
              id: Date.now().toString() + '_result',
              type: 'assistant',
              content: result.final_answer || 'Analysis completed but no answer generated.',
              timestamp: new Date(),
              steps: {
                total_steps: result.total_steps,
                execution_time: result.execution_time,
                retrieval_results: result.retrieval_results,
                llm_analysis: result.llm_analysis,
                external_actions: result.external_actions
              }
            };
            
            setMessages(prev => [...prev, resultMessage]);
            break;
          } else if (result.status === 'failed') {
            setMessages(prev => prev.filter(msg => msg.runId !== run_id));
            setMessages(prev => [...prev, {
              id: Date.now().toString() + '_error',
              type: 'system',
              content: '❌ Analysis failed. Please try again or check if you have documents uploaded.',
              timestamp: new Date()
            }]);
            break;
          }
        }
        
        attempts++;
      }
      
      if (attempts >= maxAttempts) {
        setMessages(prev => prev.filter(msg => msg.runId !== run_id));
        setMessages(prev => [...prev, {
          id: Date.now().toString() + '_timeout',
          type: 'system',
          content: '⏰ Analysis is taking longer than expected. Please try again.',
          timestamp: new Date()
        }]);
      }

    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString() + '_error',
        type: 'system',
        content: '❌ Failed to process your question. Please make sure the backend is running and try again.',
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
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI Document Chat</h1>
            <p className="text-gray-600">
              {selectedDocument 
                ? `Chatting about document: ${selectedDocument}` 
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
              💡 Try: "What are the main topics?", "Summarize the key findings", "What recommendations are made?"
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