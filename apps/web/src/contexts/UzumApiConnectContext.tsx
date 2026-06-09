import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useLanguage } from "@/contexts/LanguageContext";
import { fetchUzumApiKey } from "@/lib/uzumApiCredentials";
import { formatUzumConnectError } from "@/lib/uzumApiErrors";
import { syncUzumReportsToService } from "@/lib/uzumApiSync";
import { toast } from "sonner";

const CONNECT_LOADING_STEP_KEYS = [
  "services.connectStepApi",
  "services.connectStepSales",
  "services.connectStepProfit",
  "services.connectStepDashboard",
] as const;

const CONNECT_STEP_DELAYS_MS = [0, 60_000, 120_000, 180_000];
const CONNECT_PROGRESS_CAP = 95;

interface StartConnectOptions {
  onSuccess?: () => void;
}

interface RefreshDataOptions {
  onNoKey?: () => void;
}

interface UzumApiConnectContextValue {
  loading: boolean;
  loadingStep: number;
  loadingProgress: number;
  error: string | null;
  warnings: string[];
  startConnect: (apiKey: string, options?: StartConnectOptions) => Promise<void>;
  refreshData: (options?: RefreshDataOptions) => Promise<void>;
  clearError: () => void;
}

const UzumApiConnectContext = createContext<UzumApiConnectContextValue | null>(null);

function UzumApiConnectProgressBanner() {
  const { t } = useLanguage();
  const { loading, loadingStep, loadingProgress } = useUzumApiConnect();

  if (!loading) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 z-[100] w-[min(100vw-2rem,28rem)] -translate-x-1/2 rounded-xl border border-border bg-card p-4 shadow-lg"
    >
      <div className="flex items-start gap-3">
        <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <span
              key={loadingStep}
              className="text-sm font-medium bg-[linear-gradient(90deg,hsl(var(--muted-foreground))_0%,hsl(var(--muted-foreground))_35%,hsl(var(--primary))_50%,hsl(var(--muted-foreground))_65%,hsl(var(--muted-foreground))_100%)] bg-[length:200%_100%] bg-clip-text text-transparent animate-text-shimmer-wave"
            >
              {t(CONNECT_LOADING_STEP_KEYS[loadingStep])}
            </span>
            <span className="shrink-0 text-sm font-medium tabular-nums">
              {Math.round(loadingProgress)}%
            </span>
          </div>
          <Progress value={loadingProgress} className="h-2" />
          <p className="text-xs text-muted-foreground">{t("services.connectInProgress")}</p>
        </div>
      </div>
    </div>
  );
}

export function UzumApiConnectProvider({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const loadingStartedAtRef = useRef<number | null>(null);
  const connectInFlightRef = useRef(false);

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

  const clearError = useCallback(() => setError(null), []);

  const startConnect = useCallback(
    async (apiKey: string, options?: StartConnectOptions) => {
      const key = apiKey.trim();
      if (!key || connectInFlightRef.current) return;

      connectInFlightRef.current = true;
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
        options?.onSuccess?.();
        window.location.reload();
      } catch (e) {
        const message = formatUzumConnectError(e, t, {
          generic: t("services.connectFailed"),
          rateLimit: t("services.rateLimit"),
        });
        setError(message);
        toast.error(message);
      } finally {
        connectInFlightRef.current = false;
        setLoading(false);
      }
    },
    [t],
  );

  const refreshData = useCallback(
    async (options?: RefreshDataOptions) => {
      if (connectInFlightRef.current) return;

      let savedKey: string | null = null;
      try {
        const data = await fetchUzumApiKey();
        savedKey = data.api_key;
      } catch {
        toast.error(t("services.refreshFailed"));
        return;
      }

      if (!savedKey?.trim()) {
        toast.error(t("services.noSavedApiKey"));
        options?.onNoKey?.();
        return;
      }

      await startConnect(savedKey);
    },
    [startConnect, t],
  );

  return (
    <UzumApiConnectContext.Provider
      value={{
        loading,
        loadingStep,
        loadingProgress,
        error,
        warnings,
        startConnect,
        refreshData,
        clearError,
      }}
    >
      {children}
      <UzumApiConnectProgressBanner />
    </UzumApiConnectContext.Provider>
  );
}

export function useUzumApiConnect() {
  const context = useContext(UzumApiConnectContext);
  if (!context) {
    throw new Error("useUzumApiConnect must be used within UzumApiConnectProvider");
  }
  return context;
}
