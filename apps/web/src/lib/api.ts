/**
 * API utility for making requests to backend with X-User-Id header
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get user_id from localStorage (dev mode)
 */
function getUserId(): string {
  const stored = localStorage.getItem('user_id');
  if (stored) {
    return stored;
  }
  
  // Default dev user_id
  const defaultUserId = '00000000-0000-0000-0000-000000000001';
  localStorage.setItem('user_id', defaultUserId);
  return defaultUserId;
}

/**
 * Set user_id in localStorage
 */
export function setUserId(userId: string): void {
  localStorage.setItem('user_id', userId);
}

/**
 * Get current user_id
 */
export function getCurrentUserId(): string {
  return getUserId();
}

/**
 * Make API request with X-User-Id header
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const userId = getUserId();
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Make GET request
 */
export async function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' });
}

/**
 * Make POST request
 */
export async function apiPost<T>(endpoint: string, data?: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  });
}
