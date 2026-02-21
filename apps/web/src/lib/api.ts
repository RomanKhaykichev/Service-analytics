/**
 * API utility for making requests to backend.
 * Uses JWT (Authorization: Bearer) when logged in; falls back to X-User-Id for dev.
 */

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearAuthTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem("user_id");
  localStorage.removeItem("dev_user_id");
}

/**
 * Headers for authenticated API calls: Bearer token if present, else X-User-Id (dev).
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return { "X-User-Id": getDevUserId() };
}

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
  
  // Try localStorage (dev_user_id or user_id from auth so both flows use same id)
  const stored = localStorage.getItem("dev_user_id") ?? localStorage.getItem("user_id");
  if (stored) {
    if (!localStorage.getItem("dev_user_id")) {
      localStorage.setItem("dev_user_id", stored);
    }
    return stored;
  }

  // Default fallback (must match backend DEFAULT_DEV_USER_ID so dev user exists)
  const defaultUserId = "00000000-0000-0000-0000-000000000001";
  localStorage.setItem("dev_user_id", defaultUserId);
  localStorage.setItem("user_id", defaultUserId);
  return defaultUserId;
}

/**
 * Build query params object for API requests
 * Filters out null, undefined, and empty string values
 */
export function buildQueryParams(params?: {
  period?: string;
  date_from?: string;
  date_to?: string;
  shopId?: string | null;
  shop?: string | null;  // Shop name (string) for seller-storage filtering
  q?: string;
  limit?: number;
  granularity?: string;
  [key: string]: any;
}): Record<string, string> {
  const result: Record<string, string> = {};
  if (!params) return result;
  
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      // Map shopId to shop_id for API (UUID-based filtering)
      // shop parameter is passed as-is (string-based filtering for seller-storage)
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
 * POST without auth (for login/register).
 */
export async function apiPostNoAuth<T>(path: string, body: any): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path);
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const text = await response.text();
      let detail = text;
      try {
        const j = JSON.parse(text);
        if (j.detail) {
          if (typeof j.detail === "string") {
            detail = j.detail;
          } else if (Array.isArray(j.detail) && j.detail.length > 0) {
            detail = j.detail.map((e: { msg?: string }) => e.msg || "").filter(Boolean).join(". ") || text;
          } else {
            detail = JSON.stringify(j.detail);
          }
        }
      } catch {
        // use text as is
      }
      throw new Error(detail || `HTTP ${response.status}`);
    }
    return response.json();
  } catch (err) {
    if (err instanceof TypeError && err.message === "Failed to fetch") {
      throw new Error(
        "Не удалось подключиться к API. Убедитесь, что: 1) сервер запущен в apps/api (uvicorn на порту 8000); 2) страница открыта через npm run dev (localhost:8080), а не файлом."
      );
    }
    throw err;
  }
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
      ...getAuthHeaders(),
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
        ...getAuthHeaders(),
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
      const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
      throw new Error(
        `Не удалось подключиться к серверу. Запустите API: откройте терминал в папке apps/api и выполните: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (адрес: ${apiUrl})`
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
        ...getAuthHeaders(),
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
      const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
      throw new Error(
        `Не удалось подключиться к серверу. Запустите API: откройте терминал в папке apps/api и выполните: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (адрес: ${apiUrl})`
      );
    }
    throw error;
  }
}

/**
 * Make PATCH request to API
 */
export async function apiPatch<T>(path: string, body: any): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path);
  
  try {
    const response = await fetch(url, {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
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
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
      throw new Error(
        `Не удалось подключиться к серверу. Запустите API: откройте терминал в папке apps/api и выполните: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (адрес: ${apiUrl})`
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
      headers: getAuthHeaders(),
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
      const apiUrl = getApiBaseUrl() || "http://127.0.0.1:8000";
      throw new Error(
        `Не удалось подключиться к серверу. Запустите API: откройте терминал в папке apps/api и выполните: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (адрес: ${apiUrl})`
      );
    }
    throw error;
  }
}
