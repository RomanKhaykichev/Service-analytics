import { apiGet, apiPut } from "@/lib/api";

export interface UzumApiKeyResponse {
  api_key: string | null;
  has_key: boolean;
}

export async function fetchUzumApiKey(): Promise<UzumApiKeyResponse> {
  return apiGet<UzumApiKeyResponse>("/api/uzum-seller/api-key");
}

export async function saveUzumApiKey(apiKey: string): Promise<UzumApiKeyResponse> {
  return apiPut<UzumApiKeyResponse>("/api/uzum-seller/api-key", { api_key: apiKey.trim() });
}
