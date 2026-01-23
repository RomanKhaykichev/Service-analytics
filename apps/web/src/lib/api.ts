/**
 * API utility for making requests to backend with X-User-Id header
 */

/**
 * Get API base URL from env or default
 * In development, use relative path to leverage Vite proxy
 * In production, use full URL from env
 */
export function getApiBaseUrl(): string {
  const apiUrl = import.meta.env.VITE_API_URL;
  
  // If VITE_API_URL is set, use it (for production or custom setup)
  if (apiUrl) {
    return apiUrl;
  }
  
  // In development, use relative path to leverage Vite proxy
  // This allows /api/* requests to be proxied to backend
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    return ''; // Empty string means relative path
  }
  
  // Fallback for production without env var
  return "http://127.0.0.1:8000";
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
 * Handles both absolute paths (starting with /) and relative paths
 */
function buildUrl(baseUrl: string, path: string, params?: Record<string, any>): string {
  // If baseUrl is empty, use relative path (for Vite proxy in development)
  if (!baseUrl) {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    let urlString = cleanPath;
    
    if (params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== null && value !== undefined && value !== "") {
          searchParams.append(key, String(value));
        }
      }
      const queryString = searchParams.toString();
      if (queryString) {
        urlString += `?${queryString}`;
      }
    }
    
    return urlString;
  }
  
  // Ensure baseUrl ends without trailing slash
  const cleanBaseUrl = baseUrl.replace(/\/$/, '');
  // Ensure path starts with / if it's an absolute path
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  
  const url = new URL(cleanPath, cleanBaseUrl);
  
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

/**
 * Make POST request to API
 */
export async function apiPost<T>(path: string, body: any): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path);
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-User-Id": getDevUserId(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Handle network errors (CORS, connection refused, etc.)
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      console.error("Network error:", {
        url,
        baseUrl,
        path,
        error: error.message
      });
      const apiUrl = getApiBaseUrl();
      throw new Error(
        `Не удалось подключиться к серверу. Проверьте, что API запущен на ${apiUrl} и CORS настроен правильно.`
      );
    }
    throw error;
  }
}

/**
 * Make PUT request to API
 */
export async function apiPut<T>(path: string, body: any): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path);
  
  try {
    const response = await fetch(url, {
      method: "PUT",
      headers: {
        "X-User-Id": getDevUserId(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Handle network errors (CORS, connection refused, etc.)
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      console.error("Network error:", {
        url,
        baseUrl,
        path,
        error: error.message
      });
      const apiUrl = getApiBaseUrl();
      throw new Error(
        `Не удалось подключиться к серверу. Проверьте, что API запущен на ${apiUrl} и CORS настроен правильно.`
      );
    }
    throw error;
  }
}

/**
 * Make DELETE request to API
 */
export async function apiDelete<T>(path: string): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path);
  
  try {
    const response = await fetch(url, {
      method: "DELETE",
      headers: {
        "X-User-Id": getDevUserId(),
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    // Handle network errors (CORS, connection refused, etc.)
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      console.error("Network error:", {
        url,
        baseUrl,
        path,
        error: error.message
      });
      const apiUrl = getApiBaseUrl();
      throw new Error(
        `Не удалось подключиться к серверу. Проверьте, что API запущен на ${apiUrl} и CORS настроен правильно.`
      );
    }
    throw error;
  }
}
