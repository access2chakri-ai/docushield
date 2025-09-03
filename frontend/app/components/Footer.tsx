"use client";

import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-16">
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Logo and Description */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center mb-4">
              <img 
                src="/docushield-logo-svg.svg" 
                alt="DocuShield Logo" 
                className="h-8 w-auto mr-3"
              />
            </div>
            <p className="text-gray-600 text-sm mb-4">
              AI-powered document intelligence platform with digital twin technology. 
              Analyze contracts, assess risks, and simulate business impacts with advanced AI.
            </p>
            <div className="flex space-x-4">
              <div className="text-sm text-gray-500">
                Powered by TiDB Serverless + Multi-LLM Factory
              </div>
            </div>
          </div>
          
          {/* Features */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
              Features
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/search" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Hybrid Search
                </Link>
              </li>
              <li>
                <Link href="/digital-twin" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Digital Twin
                </Link>
              </li>
              <li>
                <Link href="/chat" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  AI Chat
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Analytics
                </Link>
              </li>
            </ul>
          </div>
          
          {/* Platform */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
              Platform
            </h3>
            <ul className="space-y-2">
              <li>
                <Link href="/documents" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  My Documents
                </Link>
              </li>
              <li>
                <Link href="/upload" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Upload
                </Link>
              </li>
              <li>
                <Link href="/auth" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Sign In
                </Link>
              </li>
              <li>
                <Link href="/demo" className="text-gray-600 hover:text-blue-600 text-sm transition-colors">
                  Demo
                </Link>
              </li>
            </ul>
          </div>
        </div>
        
        {/* Bottom Section */}
        <div className="border-t border-gray-200 pt-8 mt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="text-sm text-gray-500">
              © 2024 DocuShield. Built for TiDB Hackathon 2024.
            </div>
            <div className="flex items-center space-x-6 mt-4 md:mt-0">
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>System Online</span>
              </div>
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                <span>API v2.0</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
