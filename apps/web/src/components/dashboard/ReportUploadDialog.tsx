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
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";

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
  { id: "sales", label: "Отчет по продажам", hint: "sells-report" },
  { id: "inventory", label: "Отчет по остаткам", hint: "left-out-report" },
  { id: "expenses", label: "Отчет по услугам", hint: "expenses-report" },
  { id: "storage", label: "Отчет по хранению", hint: "seller-storage-report" },
];

export function ReportUploadDialog() {
  const [open, setOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, UploadedFile>>({});
  const [adIds, setAdIds] = useState<Record<string, string>>({});
  const [products, setProducts] = useState<ProductMapping[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [lastUploadDate, setLastUploadDate] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadProducts();
      loadLastUpload();
    }
  }, [open]);

  const loadProducts = async () => {
    const { data } = await supabase
      .from('products')
      .select('id, uzum_product_id, name')
      .limit(20);
    
    if (data) {
      setProducts(data);
    }
  };

  const loadLastUpload = async () => {
    const { data } = await supabase
      .from('report_uploads')
      .select('created_at')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    if (data) {
      const date = new Date(data.created_at);
      setLastUploadDate(date.toLocaleDateString('ru-RU'));
    }
  };

  const handleFileUpload = (reportId: string, file: File | null) => {
    setUploadedFiles(prev => ({
      ...prev,
      [reportId]: { name: file?.name || "", file, status: 'pending' }
    }));
  };

  const handleAdIdChange = (productId: string, value: string) => {
    setAdIds(prev => ({
      ...prev,
      [productId]: value
    }));
  };

  const uploadFile = async (reportId: string, fileData: UploadedFile): Promise<boolean> => {
    if (!fileData.file) return false;

    setUploadedFiles(prev => ({
      ...prev,
      [reportId]: { ...prev[reportId], status: 'uploading' }
    }));

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      const formData = new FormData();
      formData.append('file', fileData.file);
      formData.append('reportType', reportId);
      formData.append('fileName', fileData.name);

      // Use AbortController with 5 minute timeout for large files
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes

      try {
        const response = await fetch(
          `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/import-xlsx`,
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
            },
            body: formData,
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || 'Upload failed');
        }

        setUploadedFiles(prev => ({
          ...prev,
          [reportId]: { 
            ...prev[reportId], 
            status: 'success',
            rowsImported: result.rowsImported,
          }
        }));

        return true;
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
      return false;
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

    for (let i = 0; i < filesToUpload.length; i++) {
      const [reportId, fileData] = filesToUpload[i];
      const success = await uploadFile(reportId, fileData);
      
      if (success) {
        successCount++;
        totalRows += uploadedFiles[reportId]?.rowsImported || 0;
      }
      
      setUploadProgress(((i + 1) / filesToUpload.length) * 100);
    }

    setUploading(false);

    if (successCount === filesToUpload.length) {
      toast.success(`Успешно загружено ${successCount} отчётов`);
      loadLastUpload();
    } else if (successCount > 0) {
      toast.warning(`Загружено ${successCount} из ${filesToUpload.length} отчётов`);
    } else {
      toast.error('Ошибка загрузки отчётов');
    }

    // Save ad mappings
    if (Object.keys(adIds).length > 0) {
      for (const [productId, adId] of Object.entries(adIds)) {
        if (adId) {
          await supabase.from('product_ad_mappings').upsert({
            product_id: productId,
            ad_id: adId,
          }, { onConflict: 'product_id,ad_id' });
        }
      }
    }
  };

  const getFileStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'uploading':
        return <Loader2 className="w-4 h-4 animate-spin text-primary" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      default:
        return null;
    }
  };

  const uploadedCount = Object.values(uploadedFiles).filter(f => f.status === 'success').length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <div className="flex flex-col items-end">
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 px-4">
            <Upload className="w-4 h-4" />
            <span className="hidden sm:inline">Загрузить отчеты</span>
          </Button>
          {lastUploadDate && (
            <span className="text-xs text-muted-foreground mt-1">
              Последняя загрузка: {lastUploadDate}
            </span>
          )}
        </div>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">Загрузка отчетов UZUM</DialogTitle>
        </DialogHeader>

        {/* Info Block */}
        <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 mt-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
            <div className="text-sm text-foreground">
              <p className="font-semibold mb-2">Как это работает?</p>
              <p className="text-muted-foreground leading-relaxed">
                Загрузите отчёты в формате <span className="font-semibold text-primary">XLSX</span> из личного кабинета UZUM. 
                Система автоматически распознает тип отчёта и импортирует данные. 
                Рекомендуем выгружать данные за максимальный период для полной аналитики.
              </p>
              <p className="mt-2 text-warning font-medium">
                ВАЖНО! Все отчёты должны быть за один и тот же период.
              </p>
            </div>
          </div>
        </div>

        {/* Upload Progress */}
        {uploading && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Загрузка отчётов...</span>
              <span className="text-sm font-medium">{Math.round(uploadProgress)}%</span>
            </div>
            <Progress value={uploadProgress} className="h-2" />
          </div>
        )}

        {/* File Upload Blocks */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {reportTypes.map((report) => {
            const fileData = uploadedFiles[report.id];
            const hasFile = fileData?.file;
            const isUploading = fileData?.status === 'uploading';
            
            return (
              <div 
                key={report.id}
                className="border border-border rounded-lg p-4 bg-muted/30"
              >
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-foreground">{report.label}</h4>
                  <div className="flex items-center gap-2">
                    {fileData && getFileStatusIcon(fileData.status)}
                    {hasFile && !isUploading && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="h-6 w-6"
                        onClick={() => handleFileUpload(report.id, null)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
                
                <label 
                  className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 cursor-pointer transition-colors ${
                    hasFile 
                      ? fileData.status === 'success' 
                        ? "border-green-500 bg-green-500/5"
                        : fileData.status === 'error'
                        ? "border-destructive bg-destructive/5"
                        : "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50 hover:bg-muted/50"
                  } ${isUploading ? 'pointer-events-none opacity-70' : ''}`}
                >
                  <input 
                    type="file" 
                    accept=".xlsx,.xls"
                    className="hidden"
                    disabled={uploading}
                    onChange={(e) => handleFileUpload(report.id, e.target.files?.[0] || null)}
                  />
                  {hasFile ? (
                    <div className="flex flex-col items-center gap-2">
                      <div className="flex items-center gap-2 text-primary">
                        <FileSpreadsheet className="w-8 h-8" />
                        <span className="text-sm font-medium truncate max-w-[150px]">
                          {fileData.name}
                        </span>
                      </div>
                      {fileData.status === 'success' && fileData.rowsImported !== undefined && (
                        <span className="text-xs text-green-600">
                          Импортировано: {fileData.rowsImported} строк
                        </span>
                      )}
                      {fileData.status === 'error' && fileData.error && (
                        <span className="text-xs text-destructive">
                          {fileData.error}
                        </span>
                      )}
                    </div>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 text-muted-foreground mb-2" />
                      <span className="text-sm text-muted-foreground text-center">
                        Перетащите файл XLSX или нажмите
                      </span>
                    </>
                  )}
                </label>
                <p className="text-xs text-muted-foreground mt-2 text-center">
                  Файл: <span className="font-mono text-primary">{report.hint}.xlsx</span>
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
                  <p className="font-semibold mb-2">Связь товаров с рекламой</p>
                  <p className="text-muted-foreground leading-relaxed">
                    Укажите ID рекламных кампаний для точного расчёта затрат на продвижение каждого товара.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 border border-border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="font-semibold text-foreground">ID товара</TableHead>
                    <TableHead className="font-semibold text-foreground">Название</TableHead>
                    <TableHead className="font-semibold text-foreground">ID рекламы</TableHead>
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
                          placeholder="Введите ID рекламы"
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

        {/* Action Buttons */}
        <div className="flex justify-between items-center mt-6">
          <div className="text-sm text-muted-foreground">
            {uploadedCount > 0 && (
              <span className="text-green-600 font-medium">
                ✓ Загружено отчётов: {uploadedCount}
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => setOpen(false)} disabled={uploading}>
              Закрыть
            </Button>
            <Button onClick={handleSave} disabled={uploading}>
              {uploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Загрузка...
                </>
              ) : (
                'Загрузить'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
