import { useState, useEffect } from "react";
import { Upload, FileSpreadsheet, Info, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
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
  { id: "inventory_old", labelKey: "report.inventoryOld", hint: "left-out-report_old" },
];

interface ReportUploadDialogProps {
  disabled?: boolean;
  /** Открыть окно «Продлить тариф» (при нажатии «Перейти на тариф Month 10» в диалоге лимита магазинов) */
  onOpenExtendTariff?: () => void;
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
        ? "Sizning Trial 10 tarifingiz bo‘yicha 1 tagacha do‘kon ulash mumkin. Yangi do‘kon qo‘shish uchun tarifni yangilang."
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

export function ReportUploadDialog({ disabled, onOpenExtendTariff }: ReportUploadDialogProps) {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, UploadedFile>>({});
  const [adIds, setAdIds] = useState<Record<string, string>>({});
  const [products, setProducts] = useState<ProductMapping[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [lastUploadDate, setLastUploadDate] = useState<string | null>(null);
  const [dragOverReportId, setDragOverReportId] = useState<string | null>(null);
  const [storeLimitDialogOpen, setStoreLimitDialogOpen] = useState(false);
  const [storeLimitData, setStoreLimitData] = useState<{ maxShops: number; currentCount: number; tariffLabel: string } | null>(null);
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

  const handleFileUpload = (reportId: string, file: File | null) => {
    if (file) {
      // Validate file extension
      const fileName = file.name.toLowerCase();
      if (!fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
        toast.error('Поддерживаются только файлы .xlsx и .xls');
        return;
      }
    }
    setUploadedFiles(prev => ({
      ...prev,
      [reportId]: { name: file?.name || "", file, status: 'pending' }
    }));
  };

  const handleDragOver = (e: React.DragEvent, reportId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverReportId(reportId);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverReportId(null);
  };

  const handleDrop = (e: React.DragEvent, reportId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverReportId(null);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(reportId, files[0]);
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

      if (anyStoreLimitExceeded && lastStoreLimitMax != null) {
        setStoreLimitData({
          maxShops: lastStoreLimitMax,
          currentCount: lastStoreLimitCurrent ?? lastStoreLimitMax,
          tariffLabel: userTariffLabel,
        });
        setTimeout(() => setStoreLimitDialogOpen(true), 150);
      } else {
        setTimeout(() => window.location.reload(), 500);
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
        return <AlertCircle className="w-3.5 h-3.5 text-destructive" />;
      default:
        return null;
    }
  };

  const uploadedCount = Object.values(uploadedFiles).filter(f => f.status === 'success').length;

  // Человекочитаемый тариф пользователя (как в профиле/админке)
  const userTariffLabel = (() => {
    const email = (user?.email ?? "").trim().toLowerCase();
    const rawPlan = (user?.plan ?? "trial").trim().toLowerCase();

    // Админы — Gold
    if (email === "mr.romanx@mail.ru" || email === "asparrow48@gmail.com") {
      return "Gold";
    }
    // Спец-аккаунты по email для Month 5 / Month 10
    if (email === "1@mail.ru") {
      return "Month 5";
    }
    if (email === "uzb@yandex.ru") {
      return "Month 10";
    }
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
  };

  return (
    <>
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <div className="flex flex-col items-end">
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 px-4"
            disabled={disabled}
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
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col bg-card border-border">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="text-xl font-semibold">{t('report.uploadTitle')}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto pr-2 -mr-2 min-h-0">
          {/* Info Block */}
          <div className="bg-primary/10 border border-primary/20 rounded-lg p-2.5 mt-3">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
            <div className="text-xs text-foreground">
              <p className="font-semibold mb-1.5 text-sm">{t('report.howItWorks')}</p>
              <ul className="text-muted-foreground leading-tight space-y-1 list-disc list-inside">
                <li>{t('report.bullet1')}</li>
                <li>{t('report.bullet2')}</li>
                <li className="text-warning font-medium">{t('report.bullet3')}</li>
              </ul>
            </div>
          </div>
        </div>

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

        {/* File Upload Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-4">
          {reportTypes.map((report) => {
            const fileData = uploadedFiles[report.id];
            const hasFile = fileData?.file;
            const isUploading = fileData?.status === 'uploading';
            
            return (
              <div 
                key={report.id}
                className="border border-border rounded-lg p-2 bg-muted/30"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <h4 className="font-medium text-sm text-foreground">{t(report.labelKey)}</h4>
                  <div className="flex items-center gap-1.5">
                    {fileData && getFileStatusIcon(fileData.status)}
                    {hasFile && !isUploading && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-5 w-5"
                        onClick={() => handleFileUpload(report.id, null)}
                      >
                        <X className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                </div>
                
                <label 
                  className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-3 min-h-[80px] cursor-pointer transition-colors ${
                    hasFile 
                      ? fileData.status === 'success' 
                        ? "border-green-500 bg-green-500/5"
                        : fileData.status === 'error'
                        ? "border-destructive bg-destructive/5"
                        : "border-primary bg-primary/5"
                      : dragOverReportId === report.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50 hover:bg-muted/50"
                  } ${isUploading ? 'pointer-events-none opacity-70' : ''}`}
                  onDragOver={(e) => handleDragOver(e, report.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, report.id)}
                >
                  <input 
                    type="file" 
                    accept=".xlsx,.xls"
                    className="hidden"
                    disabled={uploading}
                    onChange={(e) => handleFileUpload(report.id, e.target.files?.[0] || null)}
                  />
                  {hasFile ? (
                    <div className="flex flex-col items-center gap-1">
                      <div className="flex items-center gap-1.5 text-primary">
                        <FileSpreadsheet className="w-5 h-5" />
                        <span className="text-xs font-medium truncate max-w-[140px]">
                          {fileData.name}
                        </span>
                      </div>
                      {fileData.status === 'success' && fileData.rowsImported !== undefined && (
                        <span className="text-[10px] text-green-600 leading-tight">
                          {t('report.importedRows').replace('{0}', String(fileData.rowsImported))}
                        </span>
                      )}
                      {fileData.status === 'error' && fileData.error && (
                        <span className="text-[10px] text-destructive leading-tight truncate max-w-[180px]">
                          {fileData.error}
                        </span>
                      )}
                    </div>
                  ) : (
                    <>
                      <Upload className="w-5 h-5 text-muted-foreground mb-1" />
                      <span className="text-xs text-muted-foreground text-center leading-tight">
                        {t('report.dragOrClick')}
                      </span>
                    </>
                  )}
                </label>
                <p className="text-[10px] text-muted-foreground mt-1 text-center leading-tight">
                  <span className="font-mono">{report.hint}.xlsx</span>
                  {report.id === "inventory_old" && (
                    <span className="block mt-0.5 text-amber-600 dark:text-amber-500">
                      {t('report.onlyLeftout')}
                    </span>
                  )}
                </p>
              </div>
            );
          })}
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
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center mt-4 flex-shrink-0 pt-2 border-t border-border/50">
          <div className="text-sm text-muted-foreground">
            {uploadedCount > 0 && (
              <span className="text-green-600 font-medium">
                ✓ Загружено отчётов: {uploadedCount}
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setOpen(false)} disabled={uploading}>
              {t('report.close')}
            </Button>
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
          </div>
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
}
