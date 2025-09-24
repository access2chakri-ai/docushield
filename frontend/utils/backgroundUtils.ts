/**
 * Utility functions for optimized background rendering
 */

export interface BackgroundConfig {
  patternClass: string;
  svgBackground: string;
  floatingElements: Array<{
    position: string;
    icon: string;
    size: string;
  }>;
  dataFlows: Array<{
    position: string;
    delay: string;
  }>;
}

export const backgroundConfigs: Record<string, BackgroundConfig> = {
  documents: {
    patternClass: 'bg-documents-pattern',
    svgBackground: '/backgrounds/documents-bg.svg',
    floatingElements: [
      { position: 'top-20 left-10', icon: '📄', size: 'text-6xl' },
      { position: 'top-40 right-20', icon: '📊', size: 'text-5xl' },
      { position: 'bottom-32 left-1/4', icon: '🔍', size: 'text-4xl' },
      { position: 'bottom-20 right-1/3', icon: '📋', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/4', delay: '0s' },
      { position: 'right-1/3', delay: '1s' },
      { position: 'left-2/3', delay: '2s' }
    ]
  },
  upload: {
    patternClass: 'bg-upload-pattern',
    svgBackground: '/backgrounds/upload-bg.svg',
    floatingElements: [
      { position: 'top-24 left-8', icon: '📤', size: 'text-6xl' },
      { position: 'top-40 right-12', icon: '☁️', size: 'text-5xl' },
      { position: 'bottom-36 left-1/4', icon: '⚡', size: 'text-4xl' },
      { position: 'bottom-20 right-1/3', icon: '✅', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/3', delay: '0.5s' },
      { position: 'right-1/4', delay: '2.5s' }
    ]
  },
  chat: {
    patternClass: 'bg-chat-pattern',
    svgBackground: '/backgrounds/chat-bg.svg',
    floatingElements: [
      { position: 'top-20 left-10', icon: '💬', size: 'text-6xl' },
      { position: 'top-36 right-8', icon: '🤖', size: 'text-5xl' },
      { position: 'bottom-32 left-1/5', icon: '💡', size: 'text-4xl' },
      { position: 'bottom-20 right-1/4', icon: '🔍', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/5', delay: '1s' },
      { position: 'right-1/5', delay: '3s' }
    ]
  },
  search: {
    patternClass: 'bg-search-pattern',
    svgBackground: '/backgrounds/search-bg.svg',
    floatingElements: [
      { position: 'top-24 left-12', icon: '🔍', size: 'text-6xl' },
      { position: 'top-40 right-10', icon: '📊', size: 'text-5xl' },
      { position: 'bottom-36 left-1/6', icon: '⚡', size: 'text-4xl' },
      { position: 'bottom-24 right-1/3', icon: '🎯', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/4', delay: '0.5s' },
      { position: 'right-1/6', delay: '2.5s' }
    ]
  },
  dashboard: {
    patternClass: 'bg-dashboard-pattern',
    svgBackground: '/backgrounds/dashboard-bg.svg',
    floatingElements: [
      { position: 'top-16 left-8', icon: '📊', size: 'text-5xl' },
      { position: 'top-32 right-16', icon: '⚠️', size: 'text-4xl' },
      { position: 'bottom-40 left-1/5', icon: '📈', size: 'text-6xl' },
      { position: 'bottom-24 right-1/4', icon: '🔍', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/5', delay: '0.5s' },
      { position: 'right-1/4', delay: '1.5s' }
    ]
  },
  auth: {
    patternClass: 'bg-auth-pattern',
    svgBackground: '/backgrounds/auth-bg.svg',
    floatingElements: [
      { position: 'top-16 left-8', icon: '🔐', size: 'text-5xl' },
      { position: 'top-32 right-12', icon: '🛡️', size: 'text-4xl' },
      { position: 'bottom-28 left-1/6', icon: '🔑', size: 'text-6xl' },
      { position: 'bottom-16 right-1/5', icon: '✨', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/4', delay: '1s' },
      { position: 'right-1/3', delay: '3s' }
    ]
  },
  digitalTwin: {
    patternClass: 'bg-digital-twin-pattern',
    svgBackground: '/backgrounds/digital-twin-bg.svg',
    floatingElements: [
      { position: 'top-20 left-8', icon: '🔗', size: 'text-6xl' },
      { position: 'top-40 right-12', icon: '⚙️', size: 'text-5xl' },
      { position: 'bottom-36 left-1/4', icon: '🧠', size: 'text-4xl' },
      { position: 'bottom-20 right-1/5', icon: '⚡', size: 'text-5xl' }
    ],
    dataFlows: [
      { position: 'left-1/3', delay: '1s' },
      { position: 'right-1/4', delay: '2s' },
      { position: 'left-2/3', delay: '3s' }
    ]
  }
};

/**
 * Check if the device supports high-performance animations
 */
export function supportsHighPerformance(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Check for reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return false;
  
  // Check device capabilities
  const connection = (navigator as any).connection;
  if (connection && connection.effectiveType && 
      ['slow-2g', '2g'].includes(connection.effectiveType)) {
    return false;
  }
  
  // Check device memory (if available)
  if ('deviceMemory' in navigator && (navigator as any).deviceMemory < 4) {
    return false;
  }
  
  return true;
}

/**
 * Get optimized background configuration based on device capabilities
 */
export function getOptimizedBackgroundConfig(
  configName: string,
  forceSimple = false
): Partial<BackgroundConfig> {
  const config = backgroundConfigs[configName];
  if (!config) return { patternClass: 'bg-gray-50', floatingElements: [], dataFlows: [] };
  
  if (forceSimple || !supportsHighPerformance()) {
    return {
      patternClass: config.patternClass,
      floatingElements: [], // Remove animations for low-performance devices
      dataFlows: []
    };
  }
  
  return config;
}

/**
 * Preload critical CSS for backgrounds
 */
export function preloadBackgroundStyles(): void {
  if (typeof document === 'undefined') return;
  
  // Create a hidden div to trigger CSS loading
  const div = document.createElement('div');
  div.className = 'bg-documents-pattern bg-upload-pattern bg-chat-pattern opacity-0 absolute -top-full';
  document.body.appendChild(div);
  
  // Remove after a brief moment
  setTimeout(() => {
    document.body.removeChild(div);
  }, 100);
}
