/** Preserve dashboard filters when navigating between `/` and `/cogs`. */

const DASHBOARD_FILTER_KEYS = ["date_from", "date_to", "shop", "tab"] as const;

function copyDashboardFilters(
  source: URLSearchParams,
  options?: { shop?: string | null },
): URLSearchParams {
  const next = new URLSearchParams();
  for (const key of DASHBOARD_FILTER_KEYS) {
    const value = source.get(key);
    if (value) next.set(key, value);
  }
  if (options && "shop" in options) {
    const shop = options.shop?.trim();
    if (shop && shop !== "all") next.set("shop", shop);
    else next.delete("shop");
  }
  return next;
}

function pathWithQuery(path: string, params: URLSearchParams): string {
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

/** Link to COGS page, keeping period / shop / active tab. */
export function buildCogsPath(
  searchParams: URLSearchParams,
  shop?: string | null,
): string {
  return pathWithQuery(
    "/cogs",
    copyDashboardFilters(searchParams, shop !== undefined ? { shop } : undefined),
  );
}

/** Link back to dashboard, keeping period / shop / tab from current URL. */
export function buildDashboardPath(searchParams: URLSearchParams): string {
  return pathWithQuery("/", copyDashboardFilters(searchParams));
}
