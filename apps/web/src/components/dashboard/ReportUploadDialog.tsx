import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import {
  Upload,
  FileSpreadsheet,
  Info,
  X,
  Loader2,
  CheckCircle,
  XCircle,
  BarChart3,
  Trophy,
  PieChart,
  Package,
  LineChart,
  ShieldCheck,
  PlayCircle,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
// TODO: Replace supabase with backend API calls
import { toast } from "sonner";
import { useLanguage } from "@/contexts/LanguageContext";
import { getAuthHeaders, getApiBaseUrl } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { Link } from "react-router-dom";
import { getUzumReportHowItWorksSteps, getStepVisualImageUrls, IMPORT_REPORTS_VIDEO_SRC } from "@/content/uzumReportHowItWorks";

interface UploadedFile {
  name: string;
  file: File | null;
  status: 'pending' | 'uploading' | 'success' | 'error';
  rowsImported?: number;
  error?: string;
}

interface ProductMapping {
  id: string;
  uzum_product_id: string;
  name: string;
}

const reportTypes = [
  { id: "sales", labelKey: "report.salesReport", hint: "sells-report" },
  { id: "expenses", labelKey: "report.expensesReport", hint: "expenses-report" },
  { id: "storage", labelKey: "report.storageReport", hint: "seller-storage-report" },
  { id: "inventory_old", labelKey: "report.inventoryOld", hint: "left-out-report" },
];

interface ReportUploadDialogProps {
  disabled?: boolean;
  /** Открыть окно «Продлить тариф» (при нажатии «Перейти на тариф Month 10» в диалоге лимита магазинов) */
  onOpenExtendTariff?: () => void;
}

export interface ReportUploadDialogHandle {
  /** `guided` — из меню «Помощь» (инструкция + видео + Telegram). По умолчанию `compact` — кнопка в шапке. */
  open: (variant?: "compact" | "guided") => void;
}

/** Диалог «Достигнут лимит магазинов» в стиле сервиса */
function StoreLimitDialog({
  open,
  onOpenChange,
  maxShops,
  currentCount,
  onOpenExtendTariff,
  tariffLabel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  maxShops: number;
  currentCount: number;
  /** Открыть окно «Продлить тариф» (только для тарифа Month 5) */
  onOpenExtendTariff?: () => void;
  /** Человекочитаемое название тарифа (Trial 10 / Month 5 / Month 10 / Gold) */
  tariffLabel: string;
}) {
  const { t, language } = useLanguage();
  const isMonth10 = tariffLabel === "Month 10";
  const nextTariff = tariffLabel === "Trial 10" ? "Month 5" : tariffLabel === "Month 5" ? "Month 10" : null;

  // Ожидаемый максимум магазинов по тарифу (для текста/отображения)
  const displayMax =
    tariffLabel === "Trial 10" ? 1 :
    tariffLabel === "Month 5" ? 5 :
    tariffLabel === "Month 10" ? 10 :
    maxShops;

  // Текст описания по тарифу (RU / UZ)
  const description =
    language === "uz"
      ? tariffLabel === "Trial 10"
        ? "Sizning Trial 10 tarifingiz bo‘yicha 1 ta do‘kongacha ulash mumkin. Yangi do‘kon qo‘shish uchun tarifni yangilang."
        : tariffLabel === "Month 5"
          ? "Sizning Month 5 tarifingiz bo‘yicha 5 tagacha do‘kon ulash mumkin. Yangi do‘kon qo‘shish uchun tarifni yangilang."
          : tariffLabel === "Month 10"
            ? "Sizning Month 10 tarifingiz bo‘yicha 10 tagacha do‘kon ulash mumkin. Yangi do‘kon qo‘shish uchun qo‘llab-quvvatlash xizmatiga murojaat qiling."
            : t("storeLimit.description").replace("{currentTariff}", tariffLabel).replace("{max}", String(displayMax))
      : tariffLabel === "Trial 10"
        ? "Ваш тариф Trial 10 позволяет подключить до 1 магазина. Чтобы добавить новый магазин, обновите тариф."
        : tariffLabel === "Month 5"
          ? "Ваш тариф Month 5 позволяет подключить до 5 магазинов. Чтобы добавить новый магазин, обновите тариф."
          : tariffLabel === "Month 10"
            ? "Ваш тариф Month 10 позволяет подключить до 10 магазинов. Чтобы добавить новый магазин, обратитесь в поддержку."
            : t("storeLimit.description").replace("{currentTariff}", tariffLabel).replace("{max}", String(displayMax));

  const connected =
    language === "uz"
      ? `Ulangan: ${currentCount} / ${displayMax}.`
      : `Подключено: ${currentCount} / ${displayMax}.`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border shadow-lg">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-foreground">
            {t("storeLimit.title")}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-1">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {description}
          </p>
          <p className="text-sm font-medium text-foreground">
            {connected}
          </p>
          {tariffLabel === "Trial 10" && (
            <p className="text-xs text-muted-foreground leading-relaxed">
              {language === "uz"
                ? "Trial 10 tarifida analitikada faqat yuklangan fayllardagi oxirgi 60 kunlik maʼlumotlar hisobga olinadi."
                : "В тарифе Trial 10 в аналитике учитываются только последние 60 дней данных из загруженных файлов."}
            </p>
          )}
          {isMonth10 ? (
            <p className="text-sm text-muted-foreground italic">
              {t("storeLimit.contactSupport")}
            </p>
          ) : nextTariff ? (
            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
              onClick={() => {
                onOpenChange(false);
                onOpenExtendTariff?.();
              }}
            >
              <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-white/90" aria-hidden />
              {t("storeLimit.upgradeButton").replace("{nextTariff}", nextTariff)}
            </Button>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function GuidedStepImageGrid({
  urls,
  stepId,
  ariaLabel,
  onTogglePreview,
}: {
  urls: string[];
  stepId: string;
  ariaLabel: string;
  onTogglePreview: (src: string) => void;
}) {
  const multi = urls.length > 1;
  return (
    <div
      className={
        multi
          ? "flex flex-row flex-nowrap gap-2 overflow-x-auto bg-slate-50/90 p-2.5 [scrollbar-width:thin] dark:bg-zinc-900/50"
          : "flex flex-col bg-slate-50/90 p-2.5 dark:bg-zinc-900/50"
      }
    >
      {urls.map((src, idx) => (
        <button
          type="button"
          key={`${stepId}-${idx}`}
          aria-label={ariaLabel}
          onClick={() => onTogglePreview(src)}
          className={
            multi
              ? "group flex min-h-[150px] w-[78%] max-w-[300px] shrink-0 cursor-zoom-in items-center justify-center overflow-hidden rounded-lg border border-slate-200/90 bg-white text-left shadow-sm outline-none ring-offset-background transition hover:border-primary/40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary/30 sm:h-auto sm:min-h-[170px] sm:w-0 sm:max-w-none sm:flex-1 sm:shrink dark:border-zinc-700 dark:bg-zinc-950/80 dark:hover:bg-zinc-900"
              : "group flex min-h-0 w-full cursor-zoom-in items-center justify-center overflow-hidden rounded-lg border border-slate-200/90 bg-white text-left shadow-sm outline-none ring-offset-background transition hover:border-primary/40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary/30 dark:border-zinc-700 dark:bg-zinc-950/80 dark:hover:bg-zinc-900"
          }
        >
          <img
            src={src}
            alt=""
            className="max-h-[200px] w-full object-contain object-top sm:max-h-[220px] pointer-events-none"
          />
        </button>
      ))}
    </div>
  );
}

/**
 * Фото продавцов с лендинга: секция отзывов «Что говорят о PROFiboard»
 * (`apps/web/src/components/landing/Testimonials.tsx`, поле `avatar` у `testimonialsRu` / `testimonialsUz`).
 * Файлы: `apps/web/public/testimonial-1.png` … `testimonial-4.png`.
 */
const LANDING_TESTIMONIAL_AVATAR_SRCS = [
  "/testimonial-1.png", // Манукин Илья (RU) / Manukin Ilya (UZ)
  "/testimonial-2.png", // Клещев Владислав / Kleshchev Vladislav
  "/testimonial-3.png", // Хаметов Аброр / Xametov Abror
  "/testimonial-4.png", // Азизов Бобур / Azizov Bobur
] as const;

export const ReportUploadDialog = forwardRef<ReportUploadDialogHandle, ReportUploadDialogProps>(
  function ReportUploadDialog({ disabled, onOpenExtendTariff }, ref) {
  const { t, language } = useLanguage();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [uploadVariant, setUploadVariant] = useState<"compact" | "guided">("compact");
  const [videoOpen, setVideoOpen] = useState(false);
  const [stepImagePreview, setStepImagePreview] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, UploadedFile>>({});
  const [adIds, setAdIds] = useState<Record<string, string>>({});
  const [products, setProducts] = useState<ProductMapping[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [lastUploadDate, setLastUploadDate] = useState<string | null>(null);
  const [dragOverAll, setDragOverAll] = useState(false);
  const [storeLimitDialogOpen, setStoreLimitDialogOpen] = useState(false);
  const [storeLimitData, setStoreLimitData] = useState<{ maxShops: number; currentCount: number; tariffLabel: string } | null>(null);

  useImperativeHandle(
    ref,
    () => ({
      open: (variant: "compact" | "guided" = "compact") => {
        if (disabled) return;
        setUploadVariant(variant);
        setOpen(true);
      },
    }),
    [disabled],
  );

  const howItWorksSteps = getUzumReportHowItWorksSteps(language).filter((s) => s.step !== 3);
  const guidedStep1Item = howItWorksSteps.find((s) => s.step === 1);
  const guidedStep2Item = howItWorksSteps.find((s) => s.step === 2);
  const guidedStep1Urls = guidedStep1Item ? getStepVisualImageUrls(guidedStep1Item) : [];
  const guidedStep2Urls = guidedStep2Item ? getStepVisualImageUrls(guidedStep2Item) : [];

  useEffect(() => {
    if (!videoOpen) {
      videoRef.current?.pause();
      return;
    }

    let removeCanPlay: (() => void) | undefined;
    let raf = 0;

    const start = (v: HTMLVideoElement) => {
      const tryPlay = () => {
        void v.play().catch(() => {});
      };
      v.currentTime = 0;
      if (v.readyState >= 3) {
        requestAnimationFrame(tryPlay);
        return;
      }
      const onCanPlay = () => tryPlay();
      v.addEventListener("canplay", onCanPlay, { once: true });
      removeCanPlay = () => v.removeEventListener("canplay", onCanPlay);
    };

    const v = videoRef.current;
    if (v) {
      start(v);
    } else {
      raf = requestAnimationFrame(() => {
        const el = videoRef.current;
        if (el) start(el);
      });
    }

    return () => {
      cancelAnimationFrame(raf);
      removeCanPlay?.();
    };
  }, [videoOpen]);

  useEffect(() => {
    if (!stepImagePreview) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setStepImagePreview(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [stepImagePreview]);

  // If we need to show StoreLimitDialog after a reload (triggered by store_limit_exceeded),
  // we persist the payload in localStorage.
  useEffect(() => {
    const key = "pending_store_limit_dialog";
    const raw = localStorage.getItem(key);
    if (!raw) return;
    try {
      const payload = JSON.parse(raw);
      if (
        payload &&
        typeof payload.maxShops === "number" &&
        typeof payload.currentCount === "number" &&
        typeof payload.tariffLabel === "string"
      ) {
        setStoreLimitData(payload);
        setStoreLimitDialogOpen(true);
      }
    } catch {
      // ignore parse errors
    } finally {
      localStorage.removeItem(key);
    }
  }, []);
  useEffect(() => {
    if (open) {
      loadProducts();
      loadLastUpload();
    }
  }, [open]);

  const loadProducts = async () => {
    // TODO: Load products from backend API
    // For now, use empty array
    setProducts([]);
  };

  const loadLastUpload = async () => {
    // TODO: Load last upload date from backend API
    // For now, use localStorage
    const stored = localStorage.getItem('last_upload_date');
    if (stored) {
      setLastUploadDate(stored);
    }
  };

  const detectReportIdByName = (fileName: string): string | null => {
    const lower = fileName.toLowerCase();
    if (lower.startsWith("sells")) return "sales";
    if (lower.startsWith("expenses")) return "expenses";
    if (lower.startsWith("seller")) return "storage";
    if (lower.startsWith("left")) return "inventory_old";
    return null;
  };

  const handleFilesSelected = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);

    setUploadedFiles((prev) => {
      const next = { ...prev };

      for (const file of files) {
        const fileNameLower = file.name.toLowerCase();
        if (!fileNameLower.endsWith(".xlsx") && !fileNameLower.endsWith(".xls")) {
          toast.error("Поддерживаются только файлы .xlsx и .xls");
          continue;
        }
        const reportId = detectReportIdByName(file.name);
        if (!reportId) {
          toast.error(`Не удалось определить тип отчета для файла "${file.name}". Переименуйте файл, чтобы он содержал одну из масок: ${reportTypes.map(r => r.hint).join(", ")}.`);
          continue;
        }
        next[reportId] = {
          name: file.name,
          file,
          status: "pending",
        };
      }

      return next;
    });
  };

  const handleGlobalDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverAll(true);
  };

  const handleGlobalDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverAll(false);
  };

  const handleGlobalDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverAll(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFilesSelected(files);
    }
  };

  const handleAdIdChange = (productId: string, value: string) => {
    setAdIds(prev => ({
      ...prev,
      [productId]: value
    }));
  };

  const uploadFile = async (reportId: string, fileData: UploadedFile): Promise<{ success: boolean; storeLimitExceeded?: boolean }> => {
    if (!fileData.file) return { success: false };

    setUploadedFiles(prev => ({
      ...prev,
      [reportId]: { ...prev[reportId], status: 'uploading' }
    }));

    try {
      // TODO: Replace with backend API call
      // For now, simulate upload
      const formData = new FormData();
      formData.append('file', fileData.file);
      formData.append('reportType', reportId);
      formData.append('fileName', fileData.name);

      // Use AbortController with 5 minute timeout for large files
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes

      try {
        const API_URL = getApiBaseUrl();
        const response = await fetch(
          `${API_URL}/api/import-xlsx`,
          {
            method: 'POST',
            headers: {
              ...getAuthHeaders(),
            },
            body: formData,
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        let result: {
          detail?: string;
          error?: string;
          rowsImported?: number;
          store_limit_exceeded?: boolean;
          store_limit_max?: number;
          store_limit_current?: number;
        } = {};
        try {
          result = await response.json();
        } catch {
          // ответ может быть не JSON (например HTML при 500)
        }

        if (!response.ok || result.error) {
          const raw = result.detail ?? result.error ?? (response.status === 401 ? 'Требуется вход в аккаунт' : 'Ошибка загрузки');
          const msg = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw.map((e: any) => e?.msg || e).join(', ') : String(raw);
          throw new Error(msg);
        }

        setUploadedFiles(prev => ({
          ...prev,
          [reportId]: { 
            ...prev[reportId], 
            status: 'success',
            rowsImported: result.rowsImported,
          }
        }));

        return {
          success: true,
          storeLimitExceeded: result.store_limit_exceeded,
          storeLimitMax: result.store_limit_max,
          storeLimitCurrent: result.store_limit_current,
        };
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        
        if (fetchError.name === 'AbortError') {
          throw new Error('Превышено время ожидания. Файл слишком большой, попробуйте разбить на части.');
        }
        throw fetchError;
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadedFiles(prev => ({
        ...prev,
        [reportId]: { 
          ...prev[reportId], 
          status: 'error',
          error: error.message || 'Ошибка загрузки',
        }
      }));
      return { success: false };
    }
  };

  const handleSave = async () => {
    const filesToUpload = Object.entries(uploadedFiles).filter(
      ([_, data]) => data.file && data.status === 'pending'
    );

    if (filesToUpload.length === 0) {
      toast.error('Выберите хотя бы один файл для загрузки');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    let successCount = 0;
    let totalRows = 0;
    let anyStoreLimitExceeded = false;
    let lastStoreLimitMax: number | undefined;
    let lastStoreLimitCurrent: number | undefined;

    for (let i = 0; i < filesToUpload.length; i++) {
      const [reportId, fileData] = filesToUpload[i];
      const { success, storeLimitExceeded, storeLimitMax, storeLimitCurrent } = await uploadFile(reportId, fileData);
      
      if (success) {
        successCount++;
        totalRows += uploadedFiles[reportId]?.rowsImported || 0;
        if (storeLimitExceeded) {
          anyStoreLimitExceeded = true;
          if (storeLimitMax != null) lastStoreLimitMax = storeLimitMax;
          if (storeLimitCurrent != null) lastStoreLimitCurrent = storeLimitCurrent;
        }
      }
      
      setUploadProgress(((i + 1) / filesToUpload.length) * 100);
    }

    setUploading(false);

    if (successCount === filesToUpload.length) {
      toast.success(`Успешно загружено ${successCount} отчётов`);
      loadLastUpload();

      // TODO: Save ad mappings to backend API
      if (Object.keys(adIds).length > 0) {
        console.log('Ad mappings to save:', adIds);
        localStorage.setItem('product_ad_mappings', JSON.stringify(adIds));
      }

      setOpen(false);

      const reload = () => setTimeout(() => window.location.reload(), 500);

      if (anyStoreLimitExceeded && lastStoreLimitMax != null) {
        const payload = {
          maxShops: lastStoreLimitMax,
          currentCount: lastStoreLimitCurrent ?? lastStoreLimitMax,
          tariffLabel: userTariffLabel,
        };
        localStorage.setItem("pending_store_limit_dialog", JSON.stringify(payload));
        reload();
      } else {
        reload();
      }
    } else if (successCount > 0) {
      toast.warning(`Загружено ${successCount} из ${filesToUpload.length} отчётов`);
    } else {
      toast.error('Ошибка загрузки отчётов');
    }
  };

  const getFileStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />;
      case 'success':
        return <CheckCircle className="w-3.5 h-3.5 text-green-500" />;
      case 'error':
        return <XCircle className="w-3.5 h-3.5 text-destructive" />;
      default:
        return null;
    }
  };

  const uploadedCount = Object.values(uploadedFiles).filter(f => f.status === 'success').length;

  // Человекочитаемый тариф пользователя (как в профиле/админке)
  const userTariffLabel = (() => {
    if (user?.is_admin) {
      return "Admin";
    }
    const rawPlan = (user?.plan ?? "trial").trim().toLowerCase();

    // План из БД
    if (!rawPlan || rawPlan === "trial") {
      return "Trial 10";
    }
    if (rawPlan === "month_5" || rawPlan === "month 5" || rawPlan === "month5") {
      return "Month 5";
    }
    if (rawPlan === "month_10" || rawPlan === "month 10" || rawPlan === "month10") {
      return "Month 10";
    }
    if (rawPlan === "gold" || rawPlan === "gold_plan") {
      return "Gold";
    }
    return user?.plan || "—";
  })();

  const handleOpenChange = (value: boolean) => {
    if (disabled) return;
    setOpen(value);
    if (!value) {
      setUploadVariant("compact");
      setStepImagePreview(null);
    }
  };

  const isGuided = uploadVariant === "guided";

  return (
    <>
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <div className="flex flex-col items-end">
          <Button
            type="button"
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 px-4"
            disabled={disabled}
            onClick={() => setUploadVariant("compact")}
          >
            <Upload className="w-4 h-4" />
            <span className="hidden sm:inline">{t('report.uploadButton')}</span>
          </Button>
          {lastUploadDate && (
            <span className="text-xs text-muted-foreground mt-1">
              {t('report.lastUpload')}: {lastUploadDate}
            </span>
          )}
        </div>
      </DialogTrigger>
      <DialogContent
        className={
          isGuided
            ? "max-w-6xl w-[calc(100vw-1.5rem)] max-h-[92vh] flex flex-col gap-0 border-slate-200/90 bg-white p-4 shadow-xl dark:border-zinc-700 dark:bg-zinc-950 sm:p-6 sm:max-w-6xl"
            : "max-w-3xl max-h-[90vh] flex flex-col bg-card border-border"
        }
      >
        <DialogHeader className="flex-shrink-0 space-y-0 border-b border-slate-200/80 pb-4 dark:border-zinc-700/80">
          {isGuided ? (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-8 pr-8 sm:pr-10">
              <div className="min-w-0 flex-1 space-y-2 text-left">
                <DialogTitle className="text-balance text-left text-xl font-bold leading-tight tracking-tight text-slate-900 dark:text-foreground sm:text-2xl">
                  {t("report.guidedHeroTitle")}
                </DialogTitle>
                <p className="max-w-full text-balance text-sm font-medium leading-snug text-slate-600 dark:text-muted-foreground sm:text-[15px] sm:leading-relaxed">
                  {t("report.guidedHeroSubtitle")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setVideoOpen(true)}
                className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border-2 border-primary bg-primary/5 px-3.5 py-2.5 text-sm font-bold text-primary shadow-sm transition-colors hover:bg-primary/10 dark:bg-primary/10 dark:hover:bg-primary/18"
              >
                <PlayCircle className="h-5 w-5 shrink-0" strokeWidth={2.25} aria-hidden />
                {t("report.watchImportVideoGuided")}
              </button>
            </div>
          ) : (
            <DialogTitle className="text-xl font-semibold">{t("report.uploadTitle")}</DialogTitle>
          )}
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pr-1 -mr-1 min-h-0 sm:pr-2 sm:-mr-2">
          {isGuided ? (
            <>
              <div className="mt-4 space-y-6">
                {/* Пропорции как на макете: левая колонка уже, шаги шире */}
                <div className="grid grid-cols-1 gap-4 sm:gap-5 lg:grid-cols-[minmax(0,3.5fr)_minmax(0,8.5fr)] lg:items-stretch lg:gap-5">
                  <div className="flex min-w-0 flex-col rounded-xl border border-slate-200/90 bg-primary/5 p-4 shadow-sm dark:border-zinc-700/90 dark:bg-primary/10">
                    <h3 className="text-sm font-bold leading-snug tracking-tight text-primary sm:text-[15px]">
                      {t("report.guidedBenefitsHeading")}
                    </h3>
                    <ul className="mt-3 space-y-2 text-left">
                      {(
                        [
                          [BarChart3, "text-primary", "bg-violet-100 dark:bg-violet-950/50"],
                          [Trophy, "text-emerald-600", "bg-emerald-100 dark:bg-emerald-950/40"],
                          [PieChart, "text-blue-600", "bg-blue-100 dark:bg-blue-950/40"],
                          [Package, "text-orange-600", "bg-orange-100 dark:bg-orange-950/40"],
                          [LineChart, "text-sky-600", "bg-sky-100 dark:bg-sky-950/40"],
                        ] as const
                      ).map(([Icon, color, tile], i) => {
                        const pairs = [
                          ["report.guidedBenefit1Title", "report.guidedBenefit1Desc"],
                          ["report.guidedBenefit2Title", "report.guidedBenefit2Desc"],
                          ["report.guidedBenefit3Title", "report.guidedBenefit3Desc"],
                          ["report.guidedBenefit4Title", "report.guidedBenefit4Desc"],
                          ["report.guidedBenefit5Title", "report.guidedBenefit5Desc"],
                        ] as const;
                        const [titleKey, descKey] = pairs[i];
                        return (
                          <li key={titleKey} className="flex items-start gap-3">
                            <span
                              className={`mt-px flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${tile}`}
                              aria-hidden
                            >
                              <Icon className={`h-5 w-5 ${color}`} strokeWidth={2.35} />
                            </span>
                            <div className="min-w-0 flex flex-col gap-0">
                              <span className="text-sm font-bold leading-tight text-slate-900 dark:text-foreground">
                                {t(titleKey)}
                              </span>
                              <span className="text-[13px] font-normal leading-tight text-slate-600 dark:text-muted-foreground">
                                {t(descKey)}
                              </span>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                    <div className="mt-4 grid grid-cols-[auto_1fr] gap-x-2.5 gap-y-1.5 rounded-lg border border-emerald-200 bg-emerald-50/95 p-3 text-left dark:border-emerald-800/60 dark:bg-emerald-950/35">
                      <ShieldCheck
                        className="row-start-1 h-7 w-7 shrink-0 self-start text-emerald-700 dark:text-emerald-300"
                        strokeWidth={2.25}
                        aria-hidden
                      />
                      <span className="row-start-1 min-w-0 self-start pt-0.5 text-xs font-bold leading-snug text-emerald-950 dark:text-emerald-50">
                        {t("report.guidedDataSafetyTitle")}
                      </span>
                      <span className="col-span-2 row-start-2 w-full text-xs font-normal leading-relaxed text-slate-600 dark:text-muted-foreground">
                        {t("report.guidedDataSafetyBody")}
                      </span>
                    </div>
                  </div>

                  <div className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-sm dark:border-zinc-700/90 dark:bg-zinc-950/60">
                    <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:flex-row lg:items-stretch">
                      <div className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_1fr_auto] content-start lg:min-h-0">
                        <div className="flex shrink-0 items-center gap-2.5 border-b border-slate-200/90 bg-violet-50/90 px-3 py-2.5 dark:border-zinc-700/80 dark:bg-violet-950/25">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground shadow-sm">
                            1
                          </span>
                          <span className="text-left text-sm font-bold leading-tight text-slate-900 dark:text-foreground">
                            {t("report.guidedStep1Title")}
                          </span>
                        </div>
                        <div className="flex min-h-0 w-full items-center justify-center">
                          <div className="w-full max-w-full shrink-0">
                            <GuidedStepImageGrid
                              urls={guidedStep1Urls}
                              stepId="g1"
                              ariaLabel={t("report.stepImageZoomAria")}
                              onTogglePreview={(src) =>
                                setStepImagePreview((prev) => (prev === src ? null : src))
                              }
                            />
                          </div>
                        </div>
                        <p className="min-h-0 whitespace-pre-line px-3 py-2.5 text-xs font-semibold leading-relaxed text-slate-800 dark:text-foreground/95 sm:text-[13px]">
                          {t("report.guidedStep1Body")}
                        </p>
                      </div>

                      <div
                        className="h-0 w-full shrink-0 border-t border-slate-400/80 dark:border-zinc-700/90 lg:h-auto lg:min-h-0 lg:w-0 lg:self-stretch lg:border-t-0 lg:border-l"
                        role="separator"
                        aria-hidden
                      />

                      <div className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_1fr_auto] content-start lg:min-h-0">
                        <div className="flex shrink-0 items-center gap-2.5 border-b border-slate-200/90 bg-violet-50/90 px-3 py-2.5 dark:border-zinc-700/80 dark:bg-violet-950/25">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground shadow-sm">
                            2
                          </span>
                          <span className="text-left text-sm font-bold leading-tight text-slate-900 dark:text-foreground">
                            {t("report.guidedStep2Title")}
                          </span>
                        </div>
                        <div className="flex min-h-0 w-full items-center justify-center">
                          <div className="w-full max-w-full shrink-0">
                            <GuidedStepImageGrid
                              urls={guidedStep2Urls}
                              stepId="g2"
                              ariaLabel={t("report.stepImageZoomAria")}
                              onTogglePreview={(src) =>
                                setStepImagePreview((prev) => (prev === src ? null : src))
                              }
                            />
                          </div>
                        </div>
                        <p className="min-h-0 whitespace-pre-line px-3 py-2.5 text-xs font-semibold leading-relaxed text-slate-800 dark:text-foreground/95 sm:text-[13px]">
                          {t("report.guidedStep2Body")}
                        </p>
                      </div>
                    </div>

                    <div
                      role="note"
                      className="flex items-start gap-2.5 border-t border-slate-200/90 bg-violet-50/90 px-3 py-2.5 dark:border-zinc-700/80 dark:bg-violet-950/20"
                    >
                      <Info
                        className="mt-0.5 h-4 w-4 shrink-0 text-slate-500 dark:text-slate-400"
                        strokeWidth={2.25}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 text-xs font-medium leading-snug text-slate-700 dark:text-slate-300 sm:text-[13px]">
                        {t("report.guidedStep1Footnote")}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-12">
                  <div className="flex flex-col gap-2.5 rounded-xl border border-violet-200/80 bg-violet-50/95 p-3 shadow-sm dark:border-violet-900/40 dark:bg-violet-950/25 sm:gap-3 sm:p-4 lg:col-span-8 lg:flex-row lg:items-center lg:justify-between lg:gap-4">
                    <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5">
                      <div className="flex shrink-0 items-center gap-2 pl-0.5">
                        <div className="flex items-center" aria-hidden>
                          {LANDING_TESTIMONIAL_AVATAR_SRCS.map((src) => (
                            <img
                              key={src}
                              src={src}
                              alt=""
                              width={36}
                              height={36}
                              loading="lazy"
                              decoding="async"
                              className="-ml-2 h-9 w-9 shrink-0 rounded-full border-[3px] border-white object-cover shadow-sm first:ml-0 dark:border-violet-950"
                            />
                          ))}
                        </div>
                        <div className="flex shrink-0 gap-0.5 text-amber-400" aria-hidden>
                          {[0, 1, 2, 3, 4].map((i) => (
                            <Star
                              key={i}
                              className="h-3.5 w-3.5 fill-amber-400 text-amber-400 sm:h-4 sm:w-4"
                            />
                          ))}
                        </div>
                      </div>
                      <p className="min-w-0 text-xs font-medium leading-tight text-slate-700 dark:text-slate-200 sm:text-[13px] sm:leading-snug">
                        <span className="font-bold text-slate-900 dark:text-foreground">
                          {t("report.guidedSocialProofBold")}{" "}
                        </span>
                        {t("report.guidedSocialProofRest")}
                      </p>
                    </div>

                    <div className="w-full shrink-0 rounded-xl border border-slate-200/90 bg-white p-3 shadow-sm dark:border-zinc-700/90 dark:bg-zinc-950/80 lg:max-w-none lg:min-w-[21rem] lg:basis-[48%] lg:shrink-0">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
                        {/* Скрин демо-дашборда: `public/images/guided-demo-dashboard-preview.png` (как на лендинге / в макете) */}
                        <div className="mx-auto shrink-0 overflow-hidden rounded-lg border border-slate-200/90 bg-slate-50 shadow-sm ring-1 ring-slate-200/50 dark:border-zinc-600 dark:bg-zinc-900 dark:ring-zinc-700/80 sm:mx-0">
                          <img
                            src="/images/guided-demo-dashboard-preview.png"
                            alt={t("report.guidedDemoPreviewAlt")}
                            width={160}
                            height={100}
                            loading="lazy"
                            decoding="async"
                            className="block h-auto max-h-[3.5rem] w-[6.5rem] max-w-full object-contain object-top sm:max-h-[4rem] sm:w-[7.25rem]"
                          />
                        </div>
                        <div className="flex min-w-0 flex-1 flex-col gap-1.5 text-center sm:text-left">
                          <p className="text-xs font-bold leading-tight text-emerald-950 dark:text-emerald-50 lg:whitespace-nowrap">
                            {t("report.guidedDemoHeading")}
                          </p>
                          <p className="text-xs font-normal leading-snug text-slate-600 dark:text-muted-foreground">
                            {t("report.guidedDemoSubtitle")}
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-9 w-full border-2 border-primary text-sm font-bold text-primary shadow-sm hover:bg-primary/10 sm:max-w-none"
                            asChild
                          >
                            <Link to="/training" onClick={() => setOpen(false)}>
                              {t("report.guidedDemoButton")}
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/95 p-3 shadow-sm dark:border-emerald-800/50 dark:bg-emerald-950/35 lg:col-span-4">
                    <div className="flex max-w-full flex-row items-center gap-3">
                      <a
                        href="https://t.me/PROFiboard"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 rounded-lg border border-white/80 bg-white p-0.5 shadow-md ring-1 ring-slate-200/80 transition-opacity hover:opacity-95 dark:border-zinc-700 dark:bg-zinc-950 dark:ring-zinc-700"
                      >
                        <img
                          src="/images/telegram-first-upload-qr.png"
                          alt={t("support.telegramQrAlt")}
                          className="h-[100px] w-[100px] object-contain"
                          width={100}
                          height={100}
                          loading="lazy"
                        />
                      </a>
                      <div className="flex min-w-0 flex-col gap-1.5">
                        <p className="text-left text-xs font-bold leading-tight text-emerald-950 dark:text-emerald-50 sm:text-[13px] sm:leading-snug">
                          {t("report.guidedTelegramHelpTitle")}
                        </p>
                        <p className="text-left text-xs font-normal leading-snug text-slate-700 dark:text-emerald-100/90 sm:text-[13px] sm:leading-relaxed">
                          {t("report.guidedTelegramHelpBody")}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-2.5 mt-3">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                <div className="text-xs text-foreground">
                  <p className="font-semibold mb-1.5 text-sm">{t("report.howItWorks")}</p>
                  <ul className="text-muted-foreground leading-tight space-y-1 list-disc list-inside">
                    <li>{t("report.bullet1")}</li>
                    <li>{t("report.bullet2")}</li>
                    <li className="text-warning font-medium">{t("report.bullet3")}</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

        {!isGuided && (
          <>
        {/* Upload Progress */}
        {uploading && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">{t('report.uploadingReports')}</span>
              <span className="text-sm font-medium">{Math.round(uploadProgress)}%</span>
            </div>
            <Progress value={uploadProgress} className="h-2" />
          </div>
        )}

        {/* File Upload Layout: left — list of reports, right — single upload field */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4 items-stretch">
          {/* Left: report list with statuses */}
          <div className="space-y-2">
            {reportTypes.map((report) => {
              const fileData = uploadedFiles[report.id];
              return (
                <div
                  key={report.id}
                  className="flex items-center justify-between border border-border rounded-lg px-3 py-2 bg-muted/30"
                >
                  <div className="flex flex-col">
                    <span className="font-medium text-sm text-foreground">
                      {t(report.labelKey)}
                    </span>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {report.hint}.xlsx
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {fileData && getFileStatusIcon(fileData.status)}
                    {fileData?.name && (
                      <span className="text-[11px] text-muted-foreground max-w-[120px] truncate">
                        {fileData.name}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: single upload field */}
          <div className="h-full flex flex-col">
            <label
              className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-4 min-h-[140px] md:h-full cursor-pointer transition-colors ${
                dragOverAll
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/50 hover:bg-muted/50"
              } ${uploading ? "pointer-events-none opacity-70" : ""}`}
              onDragOver={handleGlobalDragOver}
              onDragLeave={handleGlobalDragLeave}
              onDrop={handleGlobalDrop}
            >
              <input
                type="file"
                accept=".xlsx,.xls"
                multiple
                className="hidden"
                disabled={uploading}
                onChange={(e) => handleFilesSelected(e.target.files)}
              />
              <Upload className="w-6 h-6 text-muted-foreground mb-2" />
              <span className="text-sm text-muted-foreground text-center leading-tight">
                {t("report.dragOrClick")}
              </span>
            </label>
            <p className="text-[11px] text-muted-foreground mt-2 leading-snug">
              Загрузите файлы{" "}
              <span className="font-mono">
                {reportTypes.map((r) => `${r.hint}.xlsx`).join(", ")}
              </span>
              .
            </p>
          </div>
        </div>

        {/* Product-Ad ID Mapping Table */}
        {products.length > 0 && (
          <>
            <div className="bg-muted/50 border border-border rounded-lg p-4 mt-6">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                <div className="text-sm text-foreground">
                  <p className="font-semibold mb-2">{t('report.productAdLink')}</p>
                  <p className="text-muted-foreground leading-relaxed">
                    {t('report.adLinkDesc')}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 border border-border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="font-semibold text-foreground">{t('product.productId')}</TableHead>
                    <TableHead className="font-semibold text-foreground">{t('product.name')}</TableHead>
                    <TableHead className="font-semibold text-foreground">{t('report.adId')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.map((product) => (
                    <TableRow key={product.id}>
                      <TableCell className="font-mono text-sm text-foreground">
                        {product.uzum_product_id}
                      </TableCell>
                      <TableCell className="text-foreground max-w-[200px] truncate">
                        {product.name}
                      </TableCell>
                      <TableCell>
                        <Input
                          placeholder={t('report.enterAdId')}
                          value={adIds[product.id] || ""}
                          onChange={(e) => handleAdIdChange(product.id, e.target.value)}
                          className="h-8 bg-background"
                          disabled={uploading}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
          </>
        )}
        </div>

        {/* Action Buttons */}
        <div
          className={`flex items-center flex-shrink-0 ${
            isGuided
              ? "mt-5 justify-end gap-3 border-t border-slate-200/90 pt-4 dark:border-zinc-700/80"
              : "mt-4 justify-between border-t border-border/50 pt-2"
          }`}
        >
          {!isGuided ? (
            <div className="text-sm text-muted-foreground">
              {uploadedCount > 0 && (
                <span className="text-green-600 font-medium">
                  ✓ Загружено отчётов: {uploadedCount}
                </span>
              )}
            </div>
          ) : null}
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={uploading}
              className={
                isGuided
                  ? "h-10 min-w-[104px] border-2 border-slate-300 bg-white font-bold text-slate-800 shadow-sm hover:bg-slate-50 dark:border-zinc-600 dark:bg-zinc-950 dark:text-foreground dark:hover:bg-zinc-900"
                  : undefined
              }
            >
              {t("report.close")}
            </Button>
            {isGuided ? (
              <Button
                onClick={() => setUploadVariant("compact")}
                disabled={uploading}
                className="h-10 min-w-[168px] font-bold shadow-md"
              >
                {t("report.uploadFilesButton")}
              </Button>
            ) : (
              <Button onClick={handleSave} disabled={uploading}>
                {uploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('report.uploadingReports')}
                  </>
                ) : (
                  t('report.upload')
                )}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>

    {stepImagePreview && typeof document !== "undefined"
      ? createPortal(
          <div
            className="fixed inset-0 z-[9999] flex cursor-zoom-out items-center justify-center bg-black/88 p-4 sm:p-10"
            role="dialog"
            aria-modal="true"
            aria-label={t("report.stepImageZoomAria")}
            onClick={() => setStepImagePreview(null)}
          >
            <button
              type="button"
              className="absolute right-3 top-3 z-[10000] cursor-pointer rounded-md bg-background/95 p-2 text-foreground shadow-md ring-1 ring-border hover:bg-muted"
              onClick={(e) => {
                e.stopPropagation();
                setStepImagePreview(null);
              }}
              aria-label={t("report.close")}
            >
              <X className="h-5 w-5" />
            </button>
            <img
              src={stepImagePreview}
              alt=""
              className="max-h-[min(90vh,calc(100dvh-4rem))] max-w-[min(100%,calc(100vw-2rem))] w-auto object-contain"
              onClick={(e) => {
                e.stopPropagation();
                setStepImagePreview(null);
              }}
            />
          </div>,
          document.body,
        )
      : null}

    <Dialog open={videoOpen} onOpenChange={setVideoOpen}>
      <DialogContent className="max-w-4xl w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-4xl overflow-hidden">
        <DialogHeader className="px-4 pt-4 pb-3 text-left">
          <DialogTitle>{t("report.importVideoModalTitle")}</DialogTitle>
        </DialogHeader>
        <div className="px-4 pb-4">
          <video
            ref={videoRef}
            src={IMPORT_REPORTS_VIDEO_SRC}
            controls
            playsInline
            className="w-full rounded-md bg-black"
            preload="auto"
          >
            {language === "uz" ? "Brauzeringiz video qo‘llab-quvvatlamaydi." : "Ваш браузер не поддерживает видео."}
          </video>
        </div>
      </DialogContent>
    </Dialog>

    {storeLimitData && (
      <StoreLimitDialog
        open={storeLimitDialogOpen}
        onOpenChange={setStoreLimitDialogOpen}
        maxShops={storeLimitData.maxShops}
        currentCount={storeLimitData.currentCount}
        onOpenExtendTariff={onOpenExtendTariff}
        tariffLabel={storeLimitData.tariffLabel}
      />
    )}
    </>
  );
});
