import { useCallback, useMemo, useState } from "react";
import { ExternalLink, KeyRound, Loader2, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiPost } from "@/lib/api";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import { UzumReportsExport } from "@/components/dashboard/UzumReportsExport";

const UZUM_API_KEY_STORAGE = "uzum_seller_api_key";
const UZUM_AUTH_MODE_STORAGE = "uzum_seller_auth_mode";
const SWAGGER_URL =
  "https://api-seller.uzum.uz/api/seller-openapi/swagger/swagger-ui/webjars/swagger-ui/index.html#/";

interface UzumEndpoint {
  method: string;
  path: string;
  summary: string;
  tags: string[];
}

interface OpenApiExploreResult {
  auth_mode: string;
  key_valid?: boolean;
  key_error?: string | null;
  key_status?: number | null;
  auth_hint?: string;
  openapi_version?: string;
  info_title?: string;
  info_description?: string;
  endpoints: UzumEndpoint[];
  tags?: { name: string; description?: string }[];
}

function formatApiError(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  const raw = err.message;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      const d = detail as { message?: string; last_detail?: string };
      return [d.message, d.last_detail].filter(Boolean).join(" — ") || fallback;
    }
  } catch {
    /* plain text */
  }
  return raw || fallback;
}

interface ProxyResult {
  url: string;
  status_code: number;
  ok: boolean;
  data: unknown;
}

export function ServicesView() {
  const { t } = useLanguage();
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(UZUM_API_KEY_STORAGE) ?? "");
  const [authMode, setAuthMode] = useState(
    () => sessionStorage.getItem(UZUM_AUTH_MODE_STORAGE) ?? "authorization_raw"
  );
  const [explore, setExplore] = useState<OpenApiExploreResult | null>(null);
  const [keyWarning, setKeyWarning] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string | null>(null);
  const [proxyResult, setProxyResult] = useState<ProxyResult | null>(null);
  const [proxyLoading, setProxyLoading] = useState(false);

  const grouped = useMemo(() => {
    if (!explore?.endpoints?.length) return [];
    const map = new Map<string, UzumEndpoint[]>();
    for (const ep of explore.endpoints) {
      const tag = ep.tags?.[0] || t("services.untagged");
      const list = map.get(tag) ?? [];
      list.push(ep);
      map.set(tag, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b, "ru"));
  }, [explore, t]);

  const connect = useCallback(async () => {
    const key = apiKey.trim();
    if (!key) {
      setError(t("services.apiKeyRequired"));
      return;
    }
    setLoading(true);
    setError(null);
    setKeyWarning(null);
    setProxyResult(null);
    try {
      const result = await apiPost<OpenApiExploreResult>("/api/uzum-seller/openapi", { api_key: key });
      setExplore(result);
      setAuthMode(result.auth_mode);
      sessionStorage.setItem(UZUM_API_KEY_STORAGE, key);
      sessionStorage.setItem(UZUM_AUTH_MODE_STORAGE, result.auth_mode);
      if (result.key_valid === false) {
        const hint = result.auth_hint ? ` ${result.auth_hint}.` : "";
        setKeyWarning(
          (result.key_error || t("services.keyInvalid")) + hint
        );
      }
    } catch (e) {
      setError(formatApiError(e, t("services.connectFailed")));
      setExplore(null);
    } finally {
      setLoading(false);
    }
  }, [apiKey, t]);

  const tryEndpoint = useCallback(
    async (ep: UzumEndpoint) => {
      const key = apiKey.trim();
      if (!key) return;
      setActivePath(`${ep.method} ${ep.path}`);
      setProxyLoading(true);
      setProxyResult(null);
      try {
        const result = await apiPost<ProxyResult>("/api/uzum-seller/proxy", {
          api_key: key,
          auth_mode: authMode,
          method: ep.method,
          path: ep.path,
        });
        setProxyResult(result);
      } catch (e) {
        setProxyResult({
          url: ep.path,
          status_code: 0,
          ok: false,
          data: e instanceof Error ? e.message : String(e),
        });
      } finally {
        setProxyLoading(false);
      }
    },
    [apiKey, authMode]
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            {t("services.title")}
          </CardTitle>
          <CardDescription>{t("services.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div className="flex-1 space-y-2">
              <Label htmlFor="uzum-api-key">{t("services.apiKeyLabel")}</Label>
              <Input
                id="uzum-api-key"
                type="password"
                autoComplete="off"
                placeholder={t("services.apiKeyPlaceholder")}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && connect()}
              />
              <p className="text-xs text-muted-foreground">{t("services.apiKeyHint")}</p>
              <p className="text-xs text-muted-foreground">{t("services.apiKeyBearerHint")}</p>
            </div>
            <Button onClick={connect} disabled={loading} className="shrink-0">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              {t("services.connect")}
            </Button>
          </div>
          <a
            href={SWAGGER_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            {t("services.swaggerLink")}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>{t("services.errorTitle")}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {keyWarning && !error && (
        <Alert variant="destructive">
          <AlertTitle>{t("services.keyWarningTitle")}</AlertTitle>
          <AlertDescription>{keyWarning}</AlertDescription>
        </Alert>
      )}

      {explore && (
        <UzumReportsExport apiKey={apiKey} disabled={loading || explore.key_valid === false} />
      )}

      {explore && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card className="min-h-[320px]">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{t("services.endpointsTitle")}</CardTitle>
              <CardDescription className="space-y-1">
                {explore.info_title && <span className="block font-medium text-foreground">{explore.info_title}</span>}
                <span>
                  {explore.endpoints.length} {t("services.endpointsCount")}
                  {explore.openapi_version ? ` · OpenAPI ${explore.openapi_version}` : ""}
                </span>
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[min(70vh,560px)] px-4 pb-4">
                <div className="space-y-6">
                  {grouped.map(([tag, endpoints]) => (
                    <div key={tag}>
                      <h4 className="text-sm font-semibold text-foreground mb-2 sticky top-0 bg-card py-1">
                        {tag}
                      </h4>
                      <ul className="space-y-1">
                        {endpoints.map((ep) => {
                          const id = `${ep.method}:${ep.path}`;
                          const isActive = activePath === `${ep.method} ${ep.path}` && proxyLoading;
                          return (
                            <li
                              key={id}
                              className="flex items-start gap-2 rounded-md border border-border/60 p-2 hover:bg-muted/40"
                            >
                              <Badge
                                variant="outline"
                                className={cn(
                                  "shrink-0 font-mono text-[10px] uppercase",
                                  ep.method === "GET" && "border-emerald-500/50 text-emerald-600",
                                  ep.method === "POST" && "border-blue-500/50 text-blue-600",
                                  ep.method === "DELETE" && "border-red-500/50 text-red-600"
                                )}
                              >
                                {ep.method}
                              </Badge>
                              <div className="flex-1 min-w-0">
                                <p className="text-xs font-mono break-all text-foreground">{ep.path}</p>
                                {ep.summary && (
                                  <p className="text-xs text-muted-foreground mt-0.5">{ep.summary}</p>
                                )}
                              </div>
                              <Button
                                type="button"
                                size="icon"
                                variant="ghost"
                                className="shrink-0 h-8 w-8"
                                disabled={proxyLoading}
                                onClick={() => tryEndpoint(ep)}
                                title={t("services.tryRequest")}
                              >
                                {isActive ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Play className="h-4 w-4" />
                                )}
                              </Button>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="min-h-[320px]">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{t("services.responseTitle")}</CardTitle>
              <CardDescription>{t("services.responseHint")}</CardDescription>
            </CardHeader>
            <CardContent>
              {!proxyResult && !proxyLoading && (
                <p className="text-sm text-muted-foreground">{t("services.pickEndpoint")}</p>
              )}
              {proxyLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("services.loading")}
                </div>
              )}
              {proxyResult && !proxyLoading && (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <Badge variant={proxyResult.ok ? "default" : "destructive"}>
                      HTTP {proxyResult.status_code}
                    </Badge>
                    <span className="font-mono text-muted-foreground break-all">{proxyResult.url}</span>
                  </div>
                  <pre className="text-xs bg-muted/50 rounded-lg p-3 overflow-auto max-h-[min(60vh,480px)] whitespace-pre-wrap break-words">
                    {typeof proxyResult.data === "string"
                      ? proxyResult.data
                      : JSON.stringify(proxyResult.data, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
