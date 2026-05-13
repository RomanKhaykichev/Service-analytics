import { forwardRef, useImperativeHandle, useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Upload, FileSpreadsheet, Info, X, Loader2, CheckCircle, XCircle } from "lucide-react";
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
            ? "max-w-4xl max-h-[92vh] flex flex-col bg-card border-border"
            : "max-w-3xl max-h-[90vh] flex flex-col bg-card border-border"
        }
      >
        <DialogHeader className="flex-shrink-0">
          <DialogTitle
            className={
              isGuided
                ? "text-base sm:text-lg font-semibold leading-snug pr-8"
                : "text-xl font-semibold"
            }
          >
            {isGuided ? t("report.uploadDialogMainTitle") : t("report.uploadTitle")}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pr-2 -mr-2 min-h-0">
          {isGuided ? (
            <>
              <div className="space-y-4 mt-1">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
                  <h3 className="text-sm font-semibold text-foreground leading-snug">
                    {t("report.uploadStepsHeading")}
                  </h3>
                  <button
                    type="button"
                    onClick={() => setVideoOpen(true)}
                    className="text-sm font-medium text-primary underline underline-offset-4 hover:text-primary/90 shrink-0"
                  >
                    {t("report.watchImportVideo")}
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {howItWorksSteps.map((item) => (
                    <div
                      key={item.step}
                      className="rounded-lg border border-border bg-muted/20 overflow-hidden flex flex-col"
                    >
                      <div className="flex items-center justify-center gap-2 py-2 px-2 bg-muted/40 border-b border-border/60">
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                          {item.step}
                        </span>
                        <span className="text-xs font-semibold text-foreground text-left leading-tight">{item.title}</span>
                      </div>
                      {(() => {
                        const urls = getStepVisualImageUrls(item);
                        const multi = urls.length > 1;
                        return (
                          <div
                            className={
                              multi
                                ? "flex flex-row flex-nowrap gap-2 overflow-x-auto bg-background/50 p-2 [scrollbar-width:thin]"
                                : "flex flex-col bg-background/50 p-2"
                            }
                          >
                            {urls.map((src, idx) => (
                              <button
                                type="button"
                                key={`${item.step}-${idx}`}
                                aria-label={t("report.stepImageZoomAria")}
                                onClick={() =>
                                  setStepImagePreview((prev) => (prev === src ? null : src))
                                }
                                className={
                                  multi
                                    ? "group flex min-h-[150px] w-[78%] max-w-[300px] shrink-0 cursor-zoom-in items-center justify-center overflow-hidden rounded border border-border/50 bg-muted/20 text-left outline-none ring-offset-background transition hover:bg-muted/35 focus-visible:ring-2 focus-visible:ring-ring sm:h-auto sm:min-h-[170px] sm:w-0 sm:max-w-none sm:flex-1 sm:shrink"
                                    : "group flex min-h-0 w-full cursor-zoom-in items-center justify-center overflow-hidden rounded border border-border/50 bg-muted/20 text-left outline-none ring-offset-background transition hover:bg-muted/35 focus-visible:ring-2 focus-visible:ring-ring"
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
                      })()}
                      <p className="text-[11px] sm:text-xs text-foreground leading-snug p-2 flex-1 whitespace-pre-line">{item.text}</p>
                      {item.step === 2 ? (
                        <div className="flex flex-col sm:flex-row gap-3 items-center p-2 border-t border-amber-200/70 dark:border-amber-800/40 bg-amber-50/90 dark:bg-amber-950/25">
                          <a
                            href="https://t.me/PROFiboard"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 rounded-md overflow-hidden ring-1 ring-border/60 bg-card hover:opacity-95 transition-opacity"
                          >
                            <img
                              src="/images/telegram-first-upload-qr.png"
                              alt={t("support.telegramQrAlt")}
                              className="w-[120px] h-[120px] object-contain"
                              width={120}
                              height={120}
                              loading="lazy"
                            />
                          </a>
                          <div className="flex min-h-0 flex-1 items-center justify-center sm:min-h-[120px] sm:justify-start">
                            <p className="text-[11px] sm:text-xs text-foreground leading-snug text-center sm:text-left">
                              {t("report.firstUploadHelp")}
                            </p>
                          </div>
                        </div>
                      ) : null}
                      {item.noticeUnderTitle ? (
                        <p className="text-[11px] sm:text-xs text-foreground leading-snug px-2 py-2 text-center bg-amber-50/90 dark:bg-amber-950/25 border-t border-amber-200/70 dark:border-amber-800/40">
                          {item.noticeUnderTitle}
                        </p>
                      ) : null}
                    </div>
                  ))}
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
          className={`flex items-center mt-4 flex-shrink-0 pt-2 border-t border-border/50 ${
            isGuided ? "justify-end" : "justify-between"
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
            <Button variant="outline" onClick={() => setOpen(false)} disabled={uploading}>
              {t('report.close')}
            </Button>
            {isGuided ? (
              <Button onClick={() => setUploadVariant("compact")} disabled={uploading}>
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
