"use client";

import { useEffect, useState } from 'react';

interface BackgroundOptimizerProps {
  patternClass: string;
  children: React.ReactNode;
  enableAnimations?: boolean;
}

export default function BackgroundOptimizer({ 
  patternClass, 
  children, 
  enableAnimations = true 
}: BackgroundOptimizerProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    // Check for reduced motion preference
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handleChange = () => setPrefersReducedMotion(mediaQuery.matches);
    mediaQuery.addEventListener('change', handleChange);
    
    // Lazy load background after component mounts
    const timer = setTimeout(() => setIsVisible(true), 100);
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
      clearTimeout(timer);
    };
  }, []);

  // Determine if we should show animations based on user preferences and prop
  const shouldShowAnimations = enableAnimations && !prefersReducedMotion;

  return (
    <div 
      className={`min-h-screen relative overflow-hidden transition-opacity duration-500 ${
        isVisible ? patternClass : 'bg-gray-50'
      } ${isVisible ? 'opacity-100' : 'opacity-90'}`}
    >
      {shouldShowAnimations && isVisible && (
        <>
          {/* Floating elements - only render if animations are enabled */}
          <div className="floating-document top-20 left-8 text-6xl" aria-hidden="true">📄</div>
          <div className="floating-document top-40 right-12 text-5xl" aria-hidden="true">📊</div>
          <div className="floating-document bottom-32 left-1/4 text-4xl" aria-hidden="true">🔍</div>
          <div className="floating-document bottom-16 right-1/3 text-5xl" aria-hidden="true">⚡</div>
          
          {/* Data flow lines */}
          <div className="data-flow top-0 left-1/4" style={{animationDelay: '0s'}} aria-hidden="true"></div>
          <div className="data-flow top-0 right-1/3" style={{animationDelay: '2s'}} aria-hidden="true"></div>
        </>
      )}
      
      {/* Content with proper z-index */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}

// Specialized background components for different page types
export function DocumentsBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-documents-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function UploadBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-upload-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function ChatBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-chat-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function SearchBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-search-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function DashboardBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-dashboard-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function AuthBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-auth-pattern">
      {children}
    </BackgroundOptimizer>
  );
}

export function DigitalTwinBackground({ children }: { children: React.ReactNode }) {
  return (
    <BackgroundOptimizer patternClass="bg-digital-twin-pattern">
      {children}
    </BackgroundOptimizer>
  );
}
