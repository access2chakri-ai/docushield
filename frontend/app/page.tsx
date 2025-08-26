"use client";

import { useState } from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            DocuShield
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Multi-step Document Analysis Agent powered by TiDB Vector Search
          </p>
          
          <div className="bg-white rounded-lg shadow-lg p-8 mb-12">
            <h2 className="text-2xl font-semibold mb-4">🤖 Agentic Workflow Demo</h2>
            <p className="text-gray-600 mb-6">
              Experience a complete multi-step AI agent that demonstrates:
            </p>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl mb-2">📄</div>
                <h3 className="font-semibold">Document Ingestion</h3>
                <p className="text-sm text-gray-600">Upload PDFs, DOCX with vector embeddings</p>
              </div>
              
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl mb-2">🔍</div>
                <h3 className="font-semibold">TiDB Vector Search</h3>
                <p className="text-sm text-gray-600">Hybrid vector + full-text search</p>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl mb-2">🧠</div>
                <h3 className="font-semibold">LLM Analysis Chain</h3>
                <p className="text-sm text-gray-600">Multi-step reasoning with OpenAI</p>
              </div>
              
              <div className="bg-orange-50 p-4 rounded-lg">
                <div className="text-2xl mb-2">🌐</div>
                <h3 className="font-semibold">External APIs</h3>
                <p className="text-sm text-gray-600">Integration with external services</p>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/upload"
                className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors"
              >
                📤 Upload Documents
              </Link>
              <Link
                href="/chat"
                className="bg-green-600 text-white px-8 py-3 rounded-lg hover:bg-green-700 transition-colors"
              >
                💬 Start Analysis
              </Link>
              <Link
                href="/demo"
                className="bg-purple-600 text-white px-8 py-3 rounded-lg hover:bg-purple-700 transition-colors"
              >
                🎬 View Demo
              </Link>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 text-left">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-xl font-semibold mb-3">🏗️ Built for TiDB Hackathon</h3>
              <ul className="text-gray-600 space-y-2">
                <li>✅ TiDB Serverless integration</li>
                <li>✅ Vector search capabilities</li>
                <li>✅ Multi-step agent workflow</li>
                <li>✅ Real-time processing</li>
              </ul>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-xl font-semibold mb-3">⚡ Technology Stack</h3>
              <ul className="text-gray-600 space-y-2">
                <li>• TiDB Vector Search</li>
                <li>• FastAPI + Python</li>
                <li>• Next.js + TypeScript</li>
                <li>• OpenAI GPT-4</li>
              </ul>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="text-xl font-semibold mb-3">🎯 Use Cases</h3>
              <ul className="text-gray-600 space-y-2">
                <li>• Document Q&A</li>
                <li>• Content analysis</li>
                <li>• Research assistance</li>
                <li>• Knowledge extraction</li>
              </ul>
            </div>
          </div>
          
          <div className="mt-12 p-6 bg-yellow-50 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">🚀 Quick Start</h3>
            <p className="text-gray-700">
              1. Upload your documents → 2. Ask questions → 3. Watch the multi-step agent work!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}