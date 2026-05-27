/**
 * API utility for making requests to backend.
 * Uses JWT (Authorization: Bearer) when logged in.
 * Refresh-токен хранится в HttpOnly cookie и используется только на сервере.
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
 * Headers for authenticated API calls: Bearer token if present.
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getAccessToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  // No auth headers when there is no token – backend will return 401 и фронт обработает разлогин.
  return {};
}

/**
 * Get API base URL from env or default
 * In development, always use relative path so Vite proxy sends /api to local backend.
 * In production: VITE_API_URL if set, otherwise '' (same-origin) — чтобы трекинг и API
 * работали на profiboard.uz, когда фронт и бэк на одном домене.
 */
export function getApiBaseUrl(): string {
  // In development, always use relative path → Vite proxy → http://127.0.0.1:8000
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    return '';
  }
  const apiUrl = import.meta.env.VITE_API_URL;
  if (apiUrl) {
    return apiUrl;
  }
  // Production без VITE_API_URL: относительный URL — запросы идут на тот же домен (profiboard.uz/api/...)
  return '';
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

const VISITOR_KEY_STORAGE = "profiboard_visitor_key";

/** Ключ посетителя для трекинга воронки (лендинг, промо). Один на сессию. */
export function getVisitorKey(): string {
  try {
    let k = sessionStorage.getItem(VISITOR_KEY_STORAGE);
    if (!k) {
      k = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `v_${Date.now()}_${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem(VISITOR_KEY_STORAGE, k);
    }
    return k;
  } catch {
    return `v_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  }
}

// --- Централизованный refresh flow ---

let refreshPromise: Promise<void> | null = null;

async function performTokenRefresh(): Promise<void> {
  if (refreshPromise) {
    return refreshPromise;
  }
  refreshPromise = (async () => {
    try {
      // Тело запроса пустое: refresh-токен берётся из HttpOnly cookie
      const res = await apiPostNoAuth<{ access_token: string; refresh_token: string }>('/api/auth/refresh', {});
      setAuthTokens(res.access_token, res.refresh_token);
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

class AuthExpiredError extends Error {
  constructor(message = 'AUTH_EXPIRED') {
    super(message);
    this.name = 'AuthExpiredError';
  }
}

function notifyAuthExpired(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("auth-expired"));
  }
}

async function handleWithRefresh(path: string, init: RequestInit): Promise<Response> {
  const baseUrl = getApiBaseUrl();
  const url = buildUrl(baseUrl, path, init.method === 'GET' ? (init as any).params : undefined);

  // Первый запрос
  let response = await fetch(url, {
    ...init,
    credentials: 'include',
  });

  if (response.status !== 401) {
    return response;
  }

  // 401: пробуем обновить access-токен через refresh cookie
  try {
    await performTokenRefresh();
  } catch {
    clearAuthTokens();
    notifyAuthExpired();
    throw new AuthExpiredError();
  }

  // Повторяем исходный запрос с обновлённым access-токеном
  const retryHeaders = {
    ...(init.headers ?? {}),
    ...getAuthHeaders(),
  };

  response = await fetch(url, {
    ...init,
    headers: retryHeaders,
    credentials: 'include',
  });

  if (response.status === 401) {
    clearAuthTokens();
    notifyAuthExpired();
    throw new AuthExpiredError();
  }

  return response;
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
      credentials: "include",
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
  const headers = {
    ...getAuthHeaders(),
  };

  const response = await handleWithRefresh(path, {
    method: "GET",
    headers,
    // params пробрасываем только для buildUrl внутри handleWithRefresh
    ...(params ? { params } as any : {}),
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
/**
 * POST request that returns a file download (blob).
 */
export async function apiPostDownload(
  path: string,
  body: Record<string, unknown>,
  filename: string
): Promise<string[]> {
  const response = await handleWithRefresh(path, {
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

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);

  const warnHeader = response.headers.get("X-Uzum-Warnings");
  if (!warnHeader) return [];
  try {
    const binary = atob(warnHeader);
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    const parsed = JSON.parse(new TextDecoder().decode(bytes)) as unknown;
    if (Array.isArray(parsed)) {
      return parsed.filter((w): w is string => typeof w === "string");
    }
  } catch {
    /* legacy plain-text header */
  }
  return [warnHeader];
}

export async function apiPost<T>(path: string, body: any): Promise<T> {
  try {
    const response = await handleWithRefresh(path, {
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
  try {
    const response = await handleWithRefresh(path, {
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
  try {
    const response = await handleWithRefresh(path, {
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
  try {
    const response = await handleWithRefresh(path, {
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

export { AuthExpiredError };
