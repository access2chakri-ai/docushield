/**
 * Authentication utilities for JWT token management
 */

export interface User {
  user_id: string;
  email: string;
  name: string;
  is_active: boolean;
  profile_photo_url?: string | null;
  profile_photo_prompt?: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  name: string;
  password: string;
}

import { config } from './config';

const API_BASE_URL = config.apiBaseUrl;

// Token storage keys
const ACCESS_TOKEN_KEY = 'docushield_access_token';
const REFRESH_TOKEN_KEY = 'docushield_refresh_token';
const USER_DATA_KEY = 'docushield_user';

/**
 * Store tokens in localStorage
 */
export function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

/**
 * Get access token from localStorage
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Get refresh token from localStorage
 */
export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Store user data in localStorage
 */
export function storeUserData(user: User): void {
  localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
}

/**
 * Get user data from localStorage
 */
export function getUserData(): User | null {
  if (typeof window === 'undefined') return null;
  const userData = localStorage.getItem(USER_DATA_KEY);
  return userData ? JSON.parse(userData) : null;
}

/**
 * Clear all authentication data
 */
export function clearAuthData(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_DATA_KEY);
}

/**
 * Check if user is authenticated (with valid, non-expired token)
 */
export function isAuthenticated(): boolean {
  const token = getAccessToken();
  if (!token) return false;
  
  // Only check if token is actually expired (not the buffer check)
  return !isTokenActuallyExpired(token);
}

/**
 * Create authorization headers for API requests
 */
export function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Decode JWT token payload (without verification)
 */
function decodeJWT(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
}

/**
 * Check if token is expired or will expire soon (within 5 minutes)
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return true;
  
  const currentTime = Math.floor(Date.now() / 1000);
  const bufferTime = 5 * 60; // 5 minutes buffer
  return payload.exp < (currentTime + bufferTime);
}

/**
 * Check if token is actually expired (no buffer)
 */
export function isTokenActuallyExpired(token: string): boolean {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return true;
  
  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}

/**
 * Get time until token expires (in minutes)
 */
export function getTokenExpirationTime(token: string): number {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return 0;
  
  const currentTime = Math.floor(Date.now() / 1000);
  const timeLeft = payload.exp - currentTime;
  return Math.max(0, Math.floor(timeLeft / 60)); // Convert to minutes
}

/**
 * Login user with email and password
 */
export async function login(credentials: LoginRequest): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(errorData.detail || 'Login failed');
  }

  const tokens: AuthTokens = await response.json();
  storeTokens(tokens);

  // Get user data from token
  const userInfo = await getCurrentUser();
  storeUserData(userInfo);
  
  // Trigger auth change event for components
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth-change'));
  }
  
  return userInfo;
}

/**
 * Register new user
 */
export async function register(userData: RegisterRequest): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(errorData.detail || 'Registration failed');
  }

  const tokens: AuthTokens = await response.json();
  storeTokens(tokens);

  // Get user data from token
  const userInfo = await getCurrentUser();
  storeUserData(userInfo);
  
  // Trigger auth change event for components
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('auth-change'));
  }
  
  return userInfo;
}

/**
 * Refresh access token using refresh token
 */
export async function refreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const tokens: AuthTokens = await response.json();
    storeTokens(tokens);
    
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Get current user info from API
 */
export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  return response.json();
}

/**
 * Reset password for a user by email
 */
export async function resetPassword(email: string, newPassword: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      email: email,
      new_password: newPassword,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Password reset failed' }));
    throw new Error(errorData.detail || 'Password reset failed');
  }
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  try {
    // Call logout endpoint (optional - mainly for logging)
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
    });
  } catch (error) {
    // Ignore errors - we'll clear local data anyway
  } finally {
    clearAuthData();
  }
}

/**
 * Make authenticated API request with automatic token refresh
 */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = config.apiTimeout // Use config timeout, can be overridden for AI operations
): Promise<Response> {
  let token = getAccessToken();
  
  // Check if token is expired or will expire soon, and try to refresh proactively
  if (token && isTokenExpired(token)) {
    console.log('Token expires soon, attempting refresh...');
    const refreshed = await refreshToken();
    if (!refreshed) {
      // Only clear auth data if token is actually expired
      if (isTokenActuallyExpired(token)) {
        clearAuthData();
        throw new Error('Session expired. Please login again.');
      }
      // If refresh failed but token is still valid, continue with current token
      console.warn('Token refresh failed, but current token is still valid');
    } else {
      token = getAccessToken();
      console.log('Token refreshed successfully');
    }
  }

  if (!token) {
    throw new Error('No authentication token available');
  }

  // Configurable timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    });

    clearTimeout(timeoutId);

    // If we get 401, try to refresh token once
    if (response.status === 401) {
      const refreshed = await refreshToken();
      if (refreshed) {
        const newToken = getAccessToken();
        const retryController = new AbortController();
        const retryTimeoutId = setTimeout(() => retryController.abort(), timeoutMs);
        
        try {
          const retryResponse = await fetch(url, {
            ...options,
            signal: retryController.signal,
            headers: {
              ...options.headers,
              Authorization: `Bearer ${newToken}`,
            },
          });
          clearTimeout(retryTimeoutId);
          return retryResponse;
        } catch (retryError) {
          clearTimeout(retryTimeoutId);
          if (retryError instanceof Error && retryError.name === 'AbortError') {
            throw new Error('Request timed out after token refresh');
          }
          throw retryError;
        }
        } else {
        clearAuthData();
        throw new Error('Session expired. Please login again.');
      }
    }

    // Handle other HTTP error status codes
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(errorText || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Unable to connect to server');
    }
    
    throw error;
  }
}
