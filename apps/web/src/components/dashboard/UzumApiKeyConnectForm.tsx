import { useCallback, useEffect, useRef, useState } from "react";
import { Eye, EyeOff, KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useLanguage } from "@/contexts/LanguageContext";
import { fetchUzumApiKey } from "@/lib/uzumApiCredentials";
import { formatUzumConnectError } from "@/lib/uzumApiErrors";
import { syncUzumReportsToService } from "@/lib/uzumApiSync";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const CONNECT_LOADING_STEP_KEYS = [
  "services.connectStepApi",
  "services.connectStepSales",
  "services.connectStepProfit",
  "services.connectStepDashboard",
] as const;

const CONNECT_STEP_DELAYS_MS = [0, 60_000, 120_000, 180_000];
const CONNECT_PROGRESS_CAP = 95;

interface UzumApiKeyConnectFormProps {
  inputId?: string;
  /** Загрузить сохранённый ключ при активации (например, при открытии диалога). */
  active?: boolean;
  disabled?: boolean;
  onSuccess?: () => void;
  className?: string;
  buttonClassName?: string;
  showLabel?: boolean;
}

export function UzumApiKeyConnectForm({
  inputId = "uzum-api-key",
  active = true,
  disabled = false,
  onSuccess,
  className,
  buttonClassName,
  showLabel = true,
}: UzumApiKeyConnectFormProps) {
  const { t } = useLanguage();
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keyLoading, setKeyLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const loadingStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) {
      setError(null);
      setWarnings([]);
      setShowKey(false);
      return;
    }
    let cancelled = false;
    setKeyLoading(true);
    fetchUzumApiKey()
      .then((data) => {
        if (!cancelled && data.api_key) {
          setApiKey(data.api_key);
        }
      })
      .catch(() => {
        /* no saved key yet */
      })
      .finally(() => {
        if (!cancelled) setKeyLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  useEffect(() => {
    if (!loading) {
      loadingStartedAtRef.current = null;
      setLoadingStep(0);
      setLoadingProgress(0);
      return;
    }

    loadingStartedAtRef.current = Date.now();
    setLoadingStep(0);
    setLoadingProgress(4);

    const stepTimers = CONNECT_STEP_DELAYS_MS.slice(1).map((delay, index) =>
      window.setTimeout(() => setLoadingStep(index + 1), delay),
    );

    const progressTimer = window.setInterval(() => {
      setLoadingProgress((current) => {
        if (current >= CONNECT_PROGRESS_CAP) return current;
        const elapsed = Date.now() - (loadingStartedAtRef.current ?? Date.now());
        const target = Math.min(
          CONNECT_PROGRESS_CAP,
          4 + (elapsed / 600_000) * (CONNECT_PROGRESS_CAP - 4),
        );
        return Math.max(current, target);
      });
    }, 400);

    return () => {
      stepTimers.forEach((timer) => window.clearTimeout(timer));
      window.clearInterval(progressTimer);
    };
  }, [loading]);

  const connect = useCallback(async () => {
    const key = apiKey.trim();
    if (!key) {
      setError(t("services.apiKeyRequired"));
      return;
    }
    setLoading(true);
    setError(null);
    setWarnings([]);
    try {
      const result = await syncUzumReportsToService(key);
      setLoadingProgress(100);
      if (result.warnings?.length) {
        setWarnings(result.warnings);
      }
      toast.success(t("services.loadDataSuccess"));
      if (onSuccess) {
        onSuccess();
      } else {
        window.location.reload();
      }
    } catch (e) {
      setError(
        formatUzumConnectError(e, t, {
          generic: t("services.connectFailed"),
          rateLimit: t("services.rateLimit"),
        }),
      );
    } finally {
      setLoading(false);
    }
  }, [apiKey, onSuccess, t]);

  const busy = loading || keyLoading || disabled;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="space-y-2">
        {showLabel && <Label htmlFor={inputId}>{t("services.apiKeyLabel")}</Label>}
        <div className="relative">
          <Input
            id={inputId}
            type={showKey ? "text" : "password"}
            autoComplete="off"
            placeholder={t("services.apiKeyPlaceholder")}
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && !busy && connect()}
            disabled={busy}
            className="pr-10"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
            onClick={() => setShowKey((v) => !v)}
            disabled={busy || !apiKey}
            aria-label={showKey ? t("profile.hidePassword") : t("profile.showPassword")}
          >
            {showKey ? (
              <EyeOff className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Eye className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </div>
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {loading && (
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between gap-3">
              <span
                key={loadingStep}
                className="text-sm font-medium bg-[linear-gradient(90deg,hsl(var(--muted-foreground))_0%,hsl(var(--muted-foreground))_35%,hsl(var(--primary))_50%,hsl(var(--muted-foreground))_65%,hsl(var(--muted-foreground))_100%)] bg-[length:200%_100%] bg-clip-text text-transparent animate-text-shimmer-wave"
              >
                {t(CONNECT_LOADING_STEP_KEYS[loadingStep])}
              </span>
              <span className="text-sm font-medium tabular-nums shrink-0">
                {Math.round(loadingProgress)}%
              </span>
            </div>
            <Progress value={loadingProgress} className="h-2" />
          </div>
        )}
      </div>

      <Button
        onClick={connect}
        disabled={busy || !apiKey.trim()}
        className={cn("w-full sm:w-auto", buttonClassName)}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <KeyRound className="h-4 w-4 mr-2" />
        )}
        {loading ? t("services.connectInProgress") : t("services.connect")}
      </Button>

      {warnings.length > 0 && (
        <Alert>
          <AlertDescription>{warnings.join(" ")}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
