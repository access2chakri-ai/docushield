'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { isAuthenticated } from '../../utils/auth';
import UserMenu from './UserMenu';

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [mounted, setMounted] = useState(false);
  
  // Function to refresh auth state
  const refreshAuthState = () => {
    if (!mounted) return;
    const authStatus = isAuthenticated();
    setIsLoggedIn(authStatus);
  };

  useEffect(() => {
    // Prevent hydration mismatch
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    
    // Initial auth check
    refreshAuthState();
    
    // Listen for storage changes (when tokens are updated)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'docushield_access_token' || e.key === 'docushield_refresh_token' || e.key === 'docushield_user') {
        refreshAuthState();
      }
    };
    
    // Listen for custom auth events
    const handleAuthChange = () => {
      refreshAuthState();
    };
    
    // Listen for page focus/visibility changes (when user returns to tab)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        refreshAuthState();
      }
    };
    
    const handleFocus = () => {
      refreshAuthState();
    };
    
    // Event listeners - purely event-driven, no polling
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [mounted]);

  return (
    <nav className="bg-white/95 backdrop-blur-md shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <img 
              src="/docushield-logo-svg.svg" 
              alt="DocuShield" 
              className="h-8 w-auto hover:opacity-80 transition-opacity duration-200"
            />
          </Link>



          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            {isLoggedIn ? (
              <>
                <Link
                  href="/dashboard"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Dashboard
                </Link>
                <Link
                  href="/search"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Search
                </Link>
                <Link
                  href="/documents"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Documents
                </Link>
                <Link
                  href="/analytics"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Analytics
                </Link>
                <Link
                  href="/chat"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  AI Chat
                </Link>
              </>
            ) : (
              <>
                <Link
                  href="/about"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  About
                </Link>
                <Link
                  href="/demo"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Demo
                </Link>
                <Link
                  href="/upload"
                  className="text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                >
                  Upload
                </Link>
              </>
            )}
          </div>

          {/* User Menu / CTA Button */}
          <div className="hidden md:flex items-center space-x-4">
            <UserMenu />
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-600 hover:text-gray-900 focus:outline-none focus:text-gray-900"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 bg-white border-t border-gray-200">
              {isLoggedIn ? (
                <>
                  <Link
                    href="/dashboard"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/search"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Search
                  </Link>
                  <Link
                    href="/documents"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Documents
                  </Link>
                  <Link
                    href="/analytics"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Analytics
                  </Link>
                  <Link
                    href="/chat"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    AI Chat
                  </Link>
                  <Link
                    href="/profile"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Profile
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    href="/about"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    About
                  </Link>
                  <Link
                    href="/demo"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Demo
                  </Link>
                  <Link
                    href="/upload"
                    className="block px-3 py-2 text-gray-600 hover:text-blue-600 transition-colors duration-200 font-medium"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Upload
                  </Link>
                  <Link
                    href="/auth"
                    className="block px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200 font-semibold text-center"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}