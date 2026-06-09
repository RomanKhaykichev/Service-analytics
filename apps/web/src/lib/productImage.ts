import { getApiBaseUrl } from "@/lib/api";

/** Готовый путь на images.uzum.uz (с расширением) — грузим напрямую, без прокси API. */
export function isResolvedUzumCdnUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.toLowerCase().endsWith("images.uzum.uz")) return false;
    const last = parsed.pathname.split("/").filter(Boolean).pop() ?? "";
    return last.includes(".");
  } catch {
    return false;
  }
}

export function getProxiedProductImageSrc(imageUrl: string): string {
  const base = getApiBaseUrl();
  return `${base}/api/charts/product-image?url=${encodeURIComponent(imageUrl)}`;
}

/**
 * URL для <img>: прямой CDN, если путь уже разрешён бэкендом;
 * иначе прокси (bare hash без суффикса).
 */
export function getProductImageSrc(imageUrl: string | null | undefined): string | null {
  const trimmed = imageUrl?.trim();
  if (!trimmed) return null;
  if (isResolvedUzumCdnUrl(trimmed)) return trimmed;
  return getProxiedProductImageSrc(trimmed);
}
