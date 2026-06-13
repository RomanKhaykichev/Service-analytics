import { getApiBaseUrl } from "@/lib/api";

export function getProxiedProductImageSrc(imageUrl: string): string {
  const base = getApiBaseUrl();
  return `${base}/api/charts/product-image?url=${encodeURIComponent(imageUrl)}`;
}

/** Always load via API proxy — CDN blocks direct hotlink from prod domain. */
export function getProductImageSrc(imageUrl: string | null | undefined): string | null {
  const trimmed = imageUrl?.trim();
  if (!trimmed) return null;
  return getProxiedProductImageSrc(trimmed);
}
