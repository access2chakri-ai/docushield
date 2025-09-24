"use client";

import { useEffect } from 'react';

interface PerformanceMonitorProps {
  pageName: string;
  enableLogging?: boolean;
}

export default function PerformanceMonitor({ 
  pageName, 
  enableLogging = false 
}: PerformanceMonitorProps) {
  useEffect(() => {
    if (!enableLogging || typeof window === 'undefined') return;

    const startTime = performance.now();

    // Monitor page load performance
    const handleLoad = () => {
      const loadTime = performance.now() - startTime;
      console.log(`[DocuShield] ${pageName} load time: ${loadTime.toFixed(2)}ms`);
      
      // Monitor memory usage if available
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        console.log(`[DocuShield] ${pageName} memory usage:`, {
          used: Math.round(memory.usedJSHeapSize / 1048576) + 'MB',
          total: Math.round(memory.totalJSHeapSize / 1048576) + 'MB',
          limit: Math.round(memory.jsHeapSizeLimit / 1048576) + 'MB'
        });
      }
    };

    // Monitor animation performance
    const monitorAnimationFrame = () => {
      let frameCount = 0;
      let lastTime = performance.now();
      
      const countFrames = () => {
        frameCount++;
        const currentTime = performance.now();
        
        if (currentTime - lastTime >= 1000) {
          const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
          if (fps < 30) {
            console.warn(`[DocuShield] ${pageName} low FPS detected: ${fps}fps`);
          }
          frameCount = 0;
          lastTime = currentTime;
        }
        
        requestAnimationFrame(countFrames);
      };
      
      requestAnimationFrame(countFrames);
    };

    if (document.readyState === 'complete') {
      handleLoad();
    } else {
      window.addEventListener('load', handleLoad);
    }

    // Start monitoring animations after a delay
    setTimeout(monitorAnimationFrame, 2000);

    return () => {
      window.removeEventListener('load', handleLoad);
    };
  }, [pageName, enableLogging]);

  return null; // This component doesn't render anything
}

// Hook for performance monitoring
export function usePerformanceMonitor(pageName: string, enableLogging = false) {
  useEffect(() => {
    if (!enableLogging || typeof window === 'undefined') return;

    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (entry.entryType === 'paint') {
          console.log(`[DocuShield] ${pageName} ${entry.name}: ${entry.startTime.toFixed(2)}ms`);
        }
        if (entry.entryType === 'largest-contentful-paint') {
          console.log(`[DocuShield] ${pageName} LCP: ${entry.startTime.toFixed(2)}ms`);
        }
      });
    });

    observer.observe({ entryTypes: ['paint', 'largest-contentful-paint'] });

    return () => observer.disconnect();
  }, [pageName, enableLogging]);
}
