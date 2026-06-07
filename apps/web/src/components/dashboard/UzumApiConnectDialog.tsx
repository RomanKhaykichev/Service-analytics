import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Eye, EyeOff, KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useLanguage } from "@/contexts/LanguageContext";
import { UzumApiInstructionPanel } from "@/components/dashboard/UzumApiInstructionPanel";
import { fetchUzumApiKey } from "@/lib/uzumApiCredentials";
import { formatUzumConnectError } from "@/lib/uzumApiErrors";
import { syncUzumReportsToService } from "@/lib/uzumApiSync";
import { toast } from "sonner";

export interface UzumApiConnectDialogHandle {
  open: () => void;
}

interface UzumApiConnectDialogProps {
  disabled?: boolean;
  showTrigger?: boolean;
}

const CONNECT_LOADING_STEP_KEYS = [
  "services.connectStepApi",
  "services.connectStepSales",
  "services.connectStepProfit",
  "services.connectStepDashboard",
] as const;

const CONNECT_STEP_DELAYS_MS = [0, 60_000, 120_000, 180_000];
const CONNECT_PROGRESS_CAP = 95;

export const UzumApiConnectDialog = forwardRef<UzumApiConnectDialogHandle, UzumApiConnectDialogProps>(
  function UzumApiConnectDialog({ disabled, showTrigger = true }, ref) {
    const { t } = useLanguage();
    const [open, setOpen] = useState(false);
    const [apiKey, setApiKey] = useState("");
    const [showKey, setShowKey] = useState(false);
    const [keyLoading, setKeyLoading] = useState(false);
    const [loading, setLoading] = useState(false);
    const [loadingStep, setLoadingStep] = useState(0);
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [warnings, setWarnings] = useState<string[]>([]);
    const loadingStartedAtRef = useRef<number | null>(null);

    useImperativeHandle(
      ref,
      () => ({
        open: () => {
          if (disabled) return;
          setOpen(true);
        },
      }),
      [disabled],
    );

    useEffect(() => {
      if (!open) return;
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
    }, [open]);

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
        setOpen(false);
        window.location.reload();
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
    }, [apiKey, t]);

    const handleOpenChange = (value: boolean) => {
      if (disabled) return;
      setOpen(value);
      if (!value) {
        setError(null);
        setWarnings([]);
        setShowKey(false);
      }
    };

    const busy = loading || keyLoading;

    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        {showTrigger && (
          <DialogTrigger asChild>
            <div className="flex flex-col items-end">
              <Button
                type="button"
                className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 px-4"
                disabled={disabled}
              >
                <KeyRound className="w-4 h-4" />
                <span className="hidden sm:inline">{t("header.connectApi")}</span>
              </Button>
            </div>
          </DialogTrigger>
        )}
        <DialogContent className="max-w-lg bg-card border-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              {t("services.title")}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <UzumApiInstructionPanel />

            <div className="space-y-2">
              <Label htmlFor="uzum-api-key-dialog">{t("services.apiKeyLabel")}</Label>
              <div className="relative">
                <Input
                  id="uzum-api-key-dialog"
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

            <Button onClick={connect} disabled={busy || !apiKey.trim()} className="w-full sm:w-auto">
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
        </DialogContent>
      </Dialog>
    );
  },
);
