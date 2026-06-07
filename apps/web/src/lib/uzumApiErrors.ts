function messageLooksLikeInvalidKey(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("invalid_uzum_api_key") ||
    lower.includes("invalid uzum api key") ||
    lower.includes("ключ не принят") ||
    lower.includes("forbidden-001") ||
    lower.includes("shop is not available") ||
    /uzum api 40[13]/.test(lower)
  );
}

function isInvalidKeyConnectError(raw: string): boolean {
  if (messageLooksLikeInvalidKey(raw)) return true;

  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      if (detail === "invalid_uzum_api_key" || messageLooksLikeInvalidKey(detail)) {
        return true;
      }
      if (detail.toLowerCase().includes("internal server error")) {
        return true;
      }
    }
  } catch {
    /* plain text */
  }

  return raw.toLowerCase().includes("internal server error");
}

/** Map Uzum API / sync errors to user-facing messages. */
export function formatUzumConnectError(
  err: unknown,
  t: (key: string) => string,
  fallbacks: { generic: string; rateLimit?: string },
): string {
  if (!(err instanceof Error)) return fallbacks.generic;
  const raw = err.message;

  if (isInvalidKeyConnectError(raw)) {
    return t("services.keyInvalidUserMessage");
  }

  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      if (detail.includes("429") && fallbacks.rateLimit) return fallbacks.rateLimit;
      return detail;
    }
  } catch {
    /* plain text */
  }

  if (raw.includes("429") && fallbacks.rateLimit) return fallbacks.rateLimit;
  return raw || fallbacks.generic;
}
