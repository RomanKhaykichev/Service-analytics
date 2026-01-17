/**
 * API utility for making requests to backend with X-User-Id header
 */

/**
 * Get API base URL from env or default
 */
export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
}

/**
 * Get dev user ID from env, localStorage, or default
 */
export function getDevUserId(): string {
  // Try env first
  const envUserId = import.meta.env.VITE_DEV_USER_ID;
  if (envUserId) {
    return envUserId;
  }
  
  // Try localStorage
  const stored = localStorage.getItem("dev_user_id");
  if (stored) {
    return stored;
  }
  
  // Default fallback
  const defaultUserId = "aa841699-dac6-45a1-b376-9c462719315d";
  localStorage.setItem("dev_user_id", defaultUserId);
  return defaultUserId;
}

/**
 * Build query params object for API requests
 * Filters out null, undefined, and empty string values
 */
export function buildQueryParams(params?: {
  period?: string;
  shopId?: string | null;
  q?: string;
  limit?: number;
  [key: string]: any;
}): Record<string, string> {
  const result: Record<string, string> = {};
  if (!params) return result;
  
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      // Map shopId to shop_id for API
      const apiKey = key === "shopId" ? "shop_id" : key;
      result[apiKey] = String(value);
    }
  }
  return result;
}

/**
 * Build URL with query params
 */
function buildUrl(baseUrl: string, path: string, params?: Record<string, any>): string {
  const url = new URL(path, baseUrl);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== null && value !== undefined && value !== "") {
        url.searchParams.append(key, String(value));
      }
    }
  }
  return url.toString();
}

/**
 * Make GET request to API
 */
export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path, params);
  
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "X-User-Id": getDevUserId(),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
}
