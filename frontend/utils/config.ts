/**
 * Frontend configuration utilities
 */

export const config = {
  // API Configuration
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  apiUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000', // Alias for compatibility
  apiTimeout: parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '120000'),
  
  // Feature flags
  enableAnalytics: process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === 'true',
  enableMonitoring: process.env.NEXT_PUBLIC_ENABLE_MONITORING === 'true',
  
  // Environment
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  
  // UI Configuration
  defaultPageSize: parseInt(process.env.NEXT_PUBLIC_DEFAULT_PAGE_SIZE || '10'),
  maxFileSize: parseInt(process.env.NEXT_PUBLIC_MAX_FILE_SIZE || '52428800'), // 50MB default
} as const;

// Validation function to ensure required config is present
export function validateConfig() {
  const required = ['apiBaseUrl', 'apiUrl'];
  const missing = required.filter(key => !config[key as keyof typeof config]);
  
  if (missing.length > 0) {
    throw new Error(`Missing required configuration: ${missing.join(', ')}`);
  }
}

// Initialize config validation
if (typeof window !== 'undefined') {
  validateConfig();
}