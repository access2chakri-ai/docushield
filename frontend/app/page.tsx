"use client";

import Link from 'next/link';

export default function Home() {

  return (
    <div className="min-h-screen bg-documents-pattern relative overflow-hidden">
      {/* Floating document elements */}
      <div className="floating-document top-20 left-10 text-6xl">📄</div>
      <div className="floating-document top-40 right-20 text-5xl">📊</div>
      <div className="floating-document bottom-32 left-1/4 text-4xl">🔍</div>
      <div className="floating-document bottom-20 right-1/3 text-5xl">📋</div>
      

      
      <div className="container mx-auto px-4 py-8 relative z-10">
        {/* Header */}
        <div className="text-center max-w-6xl mx-auto mb-16">

          
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <Link href="/" className="hover:opacity-80 transition-opacity duration-200">
              <img 
                src="/docushield-logo-svg.svg" 
                alt="DocuShield Logo" 
                className="h-16 md:h-20 w-auto cursor-pointer"
              />
            </Link>
          </div>
          
          {/* Hero Illustration */}
          <div className="flex justify-center mb-8 relative">
            <div className="relative">
              <img 
                src="/docushield-hero-illustration.svg" 
                alt="DocuShield Hero Illustration" 
                className="w-full max-w-4xl h-auto drop-shadow-lg"
              />
              {/* Floating elements for extra visual appeal */}
              <div className="absolute -top-4 -right-4 w-8 h-8 bg-blue-500 rounded-full opacity-20 animate-bounce"></div>
              <div className="absolute -bottom-2 -left-2 w-6 h-6 bg-purple-500 rounded-full opacity-30 animate-pulse"></div>
              <div className="absolute top-1/2 -right-8 w-4 h-4 bg-green-500 rounded-full opacity-25 animate-ping"></div>
            </div>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            AI-Powered Document Intelligence
          </h1>
          <p className="text-xl text-gray-600 mb-6 font-medium">
            Enterprise document analysis with multi-LLM AI, real-time enrichment, and intelligent risk assessment
          </p>
          <p className="text-sm text-gray-500 mb-8">
            Multi-LLM • MCP Integration • TiDB Vector Search • Enterprise Security
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/upload"
              className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold"
            >
              Start Analyzing Documents
            </Link>
            <Link
              href="/about"
              className="bg-white text-blue-600 px-8 py-3 rounded-lg border-2 border-blue-600 hover:bg-blue-50 transition-colors duration-200 font-semibold"
            >
              Learn More
            </Link>
          </div>
        </div>


        {/* Features Section */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-12">
          <h2 className="text-3xl font-bold text-center mb-8">🚀 Enterprise AI Features</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-4xl mb-4">🧠</div>
              <h3 className="text-xl font-semibold mb-3">Multi-LLM Intelligence</h3>
              <p className="text-gray-600">
                OpenAI, Anthropic, Gemini, Groq, and AWS Bedrock with intelligent routing
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold mb-3">Smart Document Search</h3>
              <p className="text-gray-600">
                Vector similarity + semantic search with TiDB vector database
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🌐</div>
              <h3 className="text-xl font-semibold mb-3">MCP Integration</h3>
              <p className="text-gray-600">
                Real-time web search, news, legal precedents, and industry data enrichment
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-3">Risk Assessment</h3>
              <p className="text-gray-600">
                AI-powered contract analysis with compliance and risk scoring
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">🔗</div>
              <h3 className="text-xl font-semibold mb-3">Enterprise Architecture</h3>
              <p className="text-gray-600">
                Multi-cluster TiDB with operational, sandbox, and analytics layers
              </p>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">⚡</div>
              <h3 className="text-xl font-semibold mb-3">Real-time Processing</h3>
              <p className="text-gray-600">
                Async document pipeline with live status updates and notifications
              </p>
            </div>
          </div>
        </div>

        {/* MCP Integration Highlight */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg p-8 mb-12 text-white">
          <div className="text-center">
            <h2 className="text-3xl font-bold mb-4">🌐 MCP Integration for Document Enrichment</h2>
            <p className="text-xl mb-6 text-blue-100">
              Enhance your document analysis with real-time external data sources
            </p>
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="text-center">
                <div className="text-4xl mb-3">🔍</div>
                <h3 className="text-lg font-semibold mb-2">Web Search</h3>
                <p className="text-blue-100 text-sm">Real-time web search for context and verification</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-3">📰</div>
                <h3 className="text-lg font-semibold mb-2">News & Trends</h3>
                <p className="text-blue-100 text-sm">Latest industry news and market trends</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-3">⚖️</div>
                <h3 className="text-lg font-semibold mb-2">Legal Precedents</h3>
                <p className="text-blue-100 text-sm">Legal case references and regulatory data</p>
              </div>
            </div>
            <Link 
              href="/demo" 
              className="inline-block bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              🎯 Try Interactive Demo
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}