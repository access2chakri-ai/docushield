/**
 * Authentication utilities for JWT token management
 */

export interface User {
  user_id: string;
  email: string;
  name: string;
  is_active: boolean;
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
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
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token);
  if (!payload || !payload.exp) return true;
  
  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
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
  options: RequestInit = {}
): Promise<Response> {
  let token = getAccessToken();
  
  // Check if token is expired and try to refresh
  if (token && isTokenExpired(token)) {
    const refreshed = await refreshToken();
    if (!refreshed) {
      clearAuthData();
      throw new Error('Session expired. Please login again.');
    }
    token = getAccessToken();
  }

  if (!token) {
    throw new Error('No authentication token available');
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });

  // If we get 401, try to refresh token once
  if (response.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      const newToken = getAccessToken();
      return fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${newToken}`,
        },
      });
    } else {
      clearAuthData();
      throw new Error('Session expired. Please login again.');
    }
  }

  return response;
}
