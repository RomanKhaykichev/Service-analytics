import { forwardRef, useCallback, useImperativeHandle, useState } from "react";
import { KeyRound, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useLanguage } from "@/contexts/LanguageContext";
import { UZUM_API_KEY_STORAGE } from "@/lib/uzumApiStorage";
import { syncUzumReportsToService } from "@/lib/uzumApiSync";
import { toast } from "sonner";

function formatApiError(err: unknown, fallback: string, rateLimitFallback?: string): string {
  if (!(err instanceof Error)) return fallback;
  const raw = err.message;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") {
      if (detail.includes("429") && rateLimitFallback) return rateLimitFallback;
      return detail;
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      const d = detail as { message?: string; last_detail?: string };
      return [d.message, d.last_detail].filter(Boolean).join(" — ") || fallback;
    }
  } catch {
    /* plain text */
  }
  if (raw.includes("429") && rateLimitFallback) return rateLimitFallback;
  return raw || fallback;
}

export interface UzumApiConnectDialogHandle {
  open: () => void;
}

interface UzumApiConnectDialogProps {
  disabled?: boolean;
  showTrigger?: boolean;
}

export const UzumApiConnectDialog = forwardRef<UzumApiConnectDialogHandle, UzumApiConnectDialogProps>(
  function UzumApiConnectDialog({ disabled, showTrigger = true }, ref) {
    const { t } = useLanguage();
    const [open, setOpen] = useState(false);
    const [apiKey, setApiKey] = useState(() => sessionStorage.getItem(UZUM_API_KEY_STORAGE) ?? "");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [warnings, setWarnings] = useState<string[]>([]);

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

    const connect = useCallback(async () => {
      const key = apiKey.trim();
      if (!key) {
        setError(t("services.apiKeyRequired"));
        return;
      }
      setLoading(true);
      setError(null);
      setWarnings([]);
      sessionStorage.setItem(UZUM_API_KEY_STORAGE, key);
      try {
        const result = await syncUzumReportsToService(key);
        if (result.warnings?.length) {
          setWarnings(result.warnings);
        }
        toast.success(t("services.loadDataSuccess"));
        setOpen(false);
        window.location.reload();
      } catch (e) {
        setError(formatApiError(e, t("services.connectFailed"), t("services.rateLimit")));
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
      }
    };

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
            <DialogDescription>{t("services.description")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="uzum-api-key-dialog">{t("services.apiKeyLabel")}</Label>
              <Input
                id="uzum-api-key-dialog"
                type="password"
                autoComplete="off"
                placeholder={t("services.apiKeyPlaceholder")}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !loading && connect()}
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground">{t("services.apiKeyHint")}</p>
              <p className="text-xs text-muted-foreground">{t("services.apiKeyBearerHint")}</p>
            </div>

            <Button onClick={connect} disabled={loading || !apiKey.trim()} className="w-full sm:w-auto">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <KeyRound className="h-4 w-4 mr-2" />
              )}
              {loading ? t("services.connectInProgress") : t("services.connect")}
            </Button>

            <p className="text-xs text-muted-foreground">{t("services.loadDataHint")}</p>

            {error && (
              <Alert variant="destructive">
                <AlertTitle>{t("services.errorTitle")}</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

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
