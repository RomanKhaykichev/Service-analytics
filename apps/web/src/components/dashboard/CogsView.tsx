import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Search, ChevronUp, ChevronDown, History, Trash2, Download, Upload, Package, CircleAlert, BadgeCheck } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ProductThumbnail } from "@/components/dashboard/ProductThumbnail";
import { useLanguage } from "@/contexts/LanguageContext";
import { apiGet, apiPut, apiDelete, apiGetDownload, apiUploadFile, buildQueryParams } from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export interface ProductCogsItem {
  barcode: string | null;
  barcode_norm: string;
  product_name: string | null;
  sku: string | null;
  product_image_url?: string | null;
  price: number | null;
  lk_cogs: number | null;
  actual_cogs: number | null;
  unit_margin: number | null;
  calculation_source: "uzum" | "profiboard";
  date: string | null;
  effective_from?: string | null;
  first_sale_date?: string | null;
}

interface ProductCogsResponse {
  items: ProductCogsItem[];
}

interface ProductCogsHistoryEntry {
  period_from: string;
  period_to: string;
  cogs: number;
  calculation_source: "uzum" | "profiboard";
  effective_from?: string | null;
  can_delete?: boolean;
}

interface ProductCogsHistoryResponse {
  product_name: string | null;
  sku: string | null;
  first_sale_date: string | null;
  items: ProductCogsHistoryEntry[];
}

interface ProductCogsTemplateUploadResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

type SortField =
  | "product_name"
  | "barcode"
  | "price"
  | "lk_cogs"
  | "actual_cogs"
  | "unit_margin"
  | "date";

type SortDirection = "asc" | "desc" | null;

interface CogsViewProps {
  shop?: string | null;
}

const HISTORY_VISIBLE_ROWS = 4;

function hasCogsValue(value: number | null | undefined): boolean {
  return value != null;
}

const PRODUCT_NAME_COLUMN_CLASS = cn(
  "sticky left-0 border-r border-border shrink-0",
  "w-[min(260px,72vw)] sm:w-[300px] md:w-[360px]",
  "max-w-[min(400px,88vw)] md:max-w-[400px]"
);

export function CogsView({ shop }: CogsViewProps) {
  const { t, language } = useLanguage();
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField | null>("product_name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [editItem, setEditItem] = useState<ProductCogsItem | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editEffectiveFrom, setEditEffectiveFrom] = useState("");
  const [historyItem, setHistoryItem] = useState<ProductCogsItem | null>(null);
  const [templateAppliedDialogOpen, setTemplateAppliedDialogOpen] = useState(false);
  const [templateAppliedCount, setTemplateAppliedCount] = useState(0);
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const todayIso = () => new Date().toISOString().slice(0, 10);

  const queryKey = ["product-cogs", shop ?? "all"];

  const { data, isLoading, isError, error } = useQuery({
    queryKey,
    queryFn: async () => {
      const params = buildQueryParams({ shop: shop ?? undefined });
      return apiGet<ProductCogsResponse>("/api/product-cogs", params);
    },
    refetchOnWindowFocus: false,
  });

  const items = data?.items ?? [];

  const metrics = useMemo(() => {
    const total = items.length;
    const withoutCogs = items.filter(
      (item) => !hasCogsValue(item.lk_cogs) && !hasCogsValue(item.actual_cogs)
    ).length;
    const profiboard = items.filter((item) => hasCogsValue(item.actual_cogs)).length;
    return { total, withoutCogs, profiboard };
  }, [items]);

  const metricCards = useMemo(
    () => [
      {
        key: "total",
        icon: <Package className="h-4 w-4" />,
        label: t("cogs.metricProducts"),
        valueClassName: "text-blue-600 dark:text-blue-400",
      },
      {
        key: "withoutCogs",
        icon: <CircleAlert className="h-4 w-4" />,
        label: t("cogs.metricWithoutCogs"),
        valueClassName: "text-destructive",
      },
      {
        key: "profiboard",
        icon: <BadgeCheck className="h-4 w-4" />,
        label: t("cogs.metricProfiboard"),
        valueClassName: "text-success",
      },
    ],
    [t]
  );

  const historyQueryKey = [
    "product-cogs-history",
    historyItem?.barcode_norm ?? "none",
  ] as const;

  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: historyQueryKey,
    queryFn: async () => {
      if (!historyItem) throw new Error("no item");
      const params = buildQueryParams({
        product_name: historyItem.product_name ?? undefined,
        sku: historyItem.sku ?? undefined,
        lk_cogs: historyItem.lk_cogs ?? undefined,
      });
      return apiGet<ProductCogsHistoryResponse>(
        `/api/product-cogs/${encodeURIComponent(historyItem.barcode_norm)}/history`,
        params
      );
    },
    enabled: !!historyItem,
    refetchOnWindowFocus: false,
  });

  const deleteHistoryMutation = useMutation({
    mutationFn: async (effectiveFrom: string) => {
      if (!historyItem) throw new Error("no item");
      const params = buildQueryParams({
        effective_from: effectiveFrom,
        product_name: historyItem.product_name ?? undefined,
        sku: historyItem.sku ?? undefined,
        lk_cogs: historyItem.lk_cogs ?? undefined,
      });
      const qs = new URLSearchParams(params).toString();
      return apiDelete<ProductCogsHistoryResponse>(
        `/api/product-cogs/${encodeURIComponent(historyItem.barcode_norm)}/history?${qs}`
      );
    },
    onSuccess: (data) => {
      queryClient.setQueryData(historyQueryKey, data);
      queryClient.invalidateQueries({ queryKey: ["product-cogs"] });
      toast.success(t("cogs.historyDeleted"));
    },
    onError: (error: Error) => {
      toast.error(error.message || t("cogs.historyDeleteError"));
    },
  });

  const saveMutation = useMutation({
    mutationFn: async ({
      item,
      actualCogs,
      effectiveFrom,
    }: {
      item: ProductCogsItem;
      actualCogs: number;
      effectiveFrom: string;
    }) => {
      return apiPut<ProductCogsItem>(
        `/api/product-cogs/${encodeURIComponent(item.barcode_norm)}`,
        {
          actual_cogs: actualCogs,
          effective_from: effectiveFrom,
          barcode: item.barcode,
          sku: item.sku,
          product_name: item.product_name,
          shop: shop ?? undefined,
        }
      );
    },
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey });
      await queryClient.invalidateQueries({ queryKey: ["product-cogs-history"] });
      toast.success(t("cogs.saved"));
      setEditItem(null);
      setEditValue("");
      setEditEffectiveFrom("");
    },
    onError: (error: Error) => {
      toast.error(error.message || t("cogs.saveError"));
    },
  });

  const downloadTemplateMutation = useMutation({
    mutationFn: async (kind: "products" | "empty") => {
      const params = buildQueryParams({ shop: shop ?? undefined, kind, lang: language });
      const filename =
        kind === "empty"
          ? language === "uz"
            ? "tannarx_bosh_shablon.xlsx"
            : "sebestoimost_pustoy_shablon.xlsx"
          : language === "uz"
            ? "tannarx_tovarlar_shabloni.xlsx"
            : "sebestoimost_tovary_shablon.xlsx";
      await apiGetDownload("/api/product-cogs/template", params, filename);
    },
    onError: (error: Error) => {
      toast.error(error.message || t("cogs.templateDownloadError"));
    },
  });

  const yearStartLabel = useMemo(() => {
    const year = new Date().getFullYear();
    return `01.01.${year}`;
  }, []);

  const uploadTemplateMutation = useMutation({
    mutationFn: async (file: File) => {
      const params = buildQueryParams({ shop: shop ?? undefined });
      return apiUploadFile<ProductCogsTemplateUploadResponse>(
        "/api/product-cogs/template",
        file,
        params
      );
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey });
      if (result.imported > 0) {
        setTemplateAppliedCount(result.imported);
        setTemplateAppliedDialogOpen(true);
      } else {
        toast.message(t("cogs.templateUploadedNone"));
      }
      if (result.errors.length > 0) {
        toast.error(result.errors.slice(0, 3).join("\n"));
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || t("cogs.templateUploadError"));
    },
  });

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      return (
        item.product_name?.toLowerCase().includes(q) ||
        item.sku?.toLowerCase().includes(q) ||
        item.barcode?.toLowerCase().includes(q)
      );
    });
  }, [items, searchQuery]);

  const sorted = useMemo(() => {
    if (!sortField || !sortDirection) return filtered;

    const pushEmptyToEnd = sortDirection === "asc" ? Infinity : -Infinity;

    return [...filtered].sort((a, b) => {
      let av: unknown = a[sortField];
      let bv: unknown = b[sortField];

      if (av == null) av = pushEmptyToEnd;
      if (bv == null) bv = pushEmptyToEnd;

      if (typeof av === "string" && typeof bv === "string") {
        return sortDirection === "asc"
          ? av.localeCompare(bv, "ru")
          : bv.localeCompare(av, "ru");
      }

      if (sortDirection === "asc") {
        return (av as number) > (bv as number) ? 1 : -1;
      }
      return (av as number) < (bv as number) ? 1 : -1;
    });
  }, [filtered, sortField, sortDirection]);

  const formatValue = (value: number | null | undefined) => {
    if (value == null) return "—";
    return new Intl.NumberFormat("ru-RU").format(Math.round(value));
  };

  const formatDate = (value: string | null) => {
    if (!value) return "—";
    try {
      const [y, m, d] = value.split("-");
      return `${d}.${m}.${y}`;
    } catch {
      return value;
    }
  };

  const formatPeriod = (from: string, to: string) => {
    if (!from || !to) return "—";
    const parse = (value: string) => {
      const [y, m, d] = value.split("-");
      if (!y || !m || !d) return null;
      return { y: Number(y), m, d };
    };
    const start = parse(from);
    const end = parse(to);
    if (!start || !end) return `${formatDate(from)} — ${formatDate(to)}`;

    const shortYear = (year: number) => String(year % 100).padStart(2, "0");
    const startPart =
      start.y === end.y
        ? `${start.d}.${start.m}`
        : `${start.d}.${start.m}.${shortYear(start.y)}`;
    const endPart = `${end.d}.${end.m}.${shortYear(end.y)}`;
    return `${startPart}-${endPart}`;
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortField(null);
        setSortDirection(null);
      } else {
        setSortDirection("asc");
      }
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const getSortIcon = (field: SortField) => {
    const isActive = sortField === field;
    return (
      <span className="flex flex-col ml-0.5 shrink-0">
        <ChevronUp
          className={cn(
            "h-3 w-3 -mb-1",
            isActive && sortDirection === "asc"
              ? "text-primary"
              : "text-muted-foreground/50"
          )}
        />
        <ChevronDown
          className={cn(
            "h-3 w-3",
            isActive && sortDirection === "desc"
              ? "text-primary"
              : "text-muted-foreground/50"
          )}
        />
      </span>
    );
  };

  const headerClassName = cn(
    "sticky top-0 z-20 select-none text-muted-foreground px-2 py-1 text-center",
    "border-b border-border bg-violet-50/95 dark:bg-violet-950/95 backdrop-blur-sm",
    "whitespace-normal leading-tight"
  );

  const SortableHeader = ({
    field,
    children,
    className,
  }: {
    field: SortField;
    children: React.ReactNode;
    className?: string;
  }) => (
    <TableHead
      className={cn(
        headerClassName,
        "cursor-pointer hover:bg-violet-100/90 dark:hover:bg-violet-900/50",
        className
      )}
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center justify-center gap-1">
        {children}
        {getSortIcon(field)}
      </div>
    </TableHead>
  );

  const StaticHeader = ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) => (
    <TableHead className={cn(headerClassName, className)}>
      <div className="flex items-center justify-center gap-1">{children}</div>
    </TableHead>
  );

  const SplitHeaderLabel = ({ line1, line2 }: { line1: string; line2: string }) => (
    <span className="flex flex-col items-center leading-tight">
      <span>{line1}</span>
      <span>{line2}</span>
    </span>
  );

  const openHistory = (item: ProductCogsItem) => {
    setHistoryItem(item);
  };

  const renderCalculationBadge = (source: "uzum" | "profiboard") =>
    source === "profiboard" ? (
      <Badge className="bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-950 dark:text-green-300">
        {t("cogs.sourceProfiboard")}
      </Badge>
    ) : (
      <Badge className="bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-950 dark:text-red-300">
        {t("cogs.sourceUzum")}
      </Badge>
    );

  const openEdit = (item: ProductCogsItem) => {
    setEditItem(item);
    setEditValue(
      item.actual_cogs != null
        ? String(item.actual_cogs)
        : item.lk_cogs != null
          ? String(item.lk_cogs)
          : ""
    );
    setEditEffectiveFrom(item.effective_from ?? item.date ?? todayIso());
  };

  const handleSave = () => {
    if (!editItem) return;
    const parsed = Number(editValue.replace(/\s/g, "").replace(",", "."));
    if (!Number.isFinite(parsed) || parsed < 0) {
      toast.error(t("cogs.invalidValue"));
      return;
    }
    if (!editEffectiveFrom.trim()) {
      toast.error(t("cogs.effectiveFromRequired"));
      return;
    }
    saveMutation.mutate({
      item: editItem,
      actualCogs: parsed,
      effectiveFrom: editEffectiveFrom,
    });
  };

  const handleUploadTemplate = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    uploadTemplateMutation.mutate(file);
  };

  return (
    <div className="w-full min-w-0 space-y-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="relative flex-1 min-w-0 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder={t("search.byNameArticle")}
            className="pl-10 bg-background"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <TooltipProvider delayDuration={200}>
          <div className="flex flex-wrap items-stretch gap-2 shrink-0">
            {metricCards.map((card) => (
              <Tooltip key={card.key}>
                <TooltipTrigger asChild>
                  <div className="rounded-xl border border-border bg-card shadow-sm px-2.5 py-2 flex items-center gap-2 cursor-default">
                    <div className="text-muted-foreground">{card.icon}</div>
                    <span
                      className={cn(
                        "text-sm font-semibold tabular-nums whitespace-nowrap",
                        card.valueClassName
                      )}
                    >
                      {isLoading
                        ? "—"
                        : metrics[card.key as keyof typeof metrics]}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">{card.label}</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>
        <div className="flex flex-wrap items-stretch gap-2 shrink-0 self-end xl:self-auto xl:ml-auto">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-auto min-w-[11rem] flex-col items-start gap-0.5 px-3 py-2 text-left"
            onClick={() => downloadTemplateMutation.mutate("products")}
            disabled={downloadTemplateMutation.isPending}
          >
            <span className="flex items-center gap-2 font-medium">
              <Download className="h-4 w-4 shrink-0" />
              {t("cogs.templateProducts")}
            </span>
            <span className="text-xs font-normal text-muted-foreground leading-snug">
              {t("cogs.templateProductsHint")}
            </span>
          </Button>
          <span className="self-center text-sm text-muted-foreground px-0.5">
            {t("common.or")}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-auto min-w-[11rem] flex-col items-start gap-0.5 px-3 py-2 text-left"
            onClick={() => downloadTemplateMutation.mutate("empty")}
            disabled={downloadTemplateMutation.isPending}
          >
            <span className="flex items-center gap-2 font-medium">
              <Download className="h-4 w-4 shrink-0" />
              {t("cogs.templateEmpty")}
            </span>
            <span className="text-xs font-normal text-muted-foreground leading-snug">
              {t("cogs.templateEmptyHint")}
            </span>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={cn(
              "h-auto w-auto flex-col items-start gap-0.5 px-2.5 py-2 text-left",
              "bg-violet-200/80 hover:bg-violet-300/90 border-violet-400 text-violet-950",
              "dark:bg-violet-900/70 dark:hover:bg-violet-800/80 dark:border-violet-600 dark:text-violet-50"
            )}
            onClick={() => uploadInputRef.current?.click()}
            disabled={uploadTemplateMutation.isPending}
          >
            <span className="flex items-center gap-2 font-medium">
              <Upload className="h-4 w-4 shrink-0" />
              {uploadTemplateMutation.isPending ? t("cogs.templateUploading") : t("cogs.uploadLine1")}
            </span>
            <span className="text-xs font-normal text-muted-foreground leading-snug">
              {t("cogs.uploadLine2")}
            </span>
          </Button>
          <input
            ref={uploadInputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={handleUploadTemplate}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-lg border border-border p-8 text-center text-muted-foreground">
          {t("cogs.loading")}
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-8 text-center text-destructive text-sm">
          {error instanceof Error ? error.message : t("cogs.loadError")}
        </div>
      ) : (
        <div className="data-table animate-fade-in w-full min-w-0 max-w-full rounded-lg border border-border">
          <div
            className={cn(
              "max-h-[min(70vh,42rem)] sm:max-h-[min(75vh,48rem)] lg:max-h-[min(78vh,52rem)]",
              "overflow-auto overscroll-contain",
              "touch-pan-x touch-pan-y [scrollbar-gutter:stable]"
            )}
          >
            <Table
              wrapperClassName="overflow-visible min-w-0"
              className="w-max min-w-full caption-bottom"
            >
              <TableHeader>
                <TableRow className="border-border">
                  <SortableHeader
                    field="product_name"
                    className={cn("z-40 text-center", PRODUCT_NAME_COLUMN_CLASS)}
                  >
                    {t("table.productName")}
                  </SortableHeader>
                  <SortableHeader field="barcode" className="min-w-[120px]">
                    {t("product.barcode")}
                  </SortableHeader>
                  <SortableHeader field="price" className="min-w-[90px]">
                    {t("table.price")}
                  </SortableHeader>
                  <SortableHeader field="lk_cogs" className="min-w-[100px]">
                    <SplitHeaderLabel
                      line1={t("cogs.lkUzumLine1")}
                      line2={t("cogs.lkUzumLine2")}
                    />
                  </SortableHeader>
                  <SortableHeader field="actual_cogs" className="min-w-[100px]">
                    <SplitHeaderLabel
                      line1={t("cogs.actualLine1")}
                      line2={t("cogs.actualLine2")}
                    />
                  </SortableHeader>
                  <SortableHeader field="unit_margin" className="min-w-[90px]">
                    {t("cogs.unitMargin")}
                  </SortableHeader>
                  <StaticHeader className="min-w-[100px]">
                    <SplitHeaderLabel
                      line1={t("cogs.calculationLine1")}
                      line2={t("cogs.calculationLine2")}
                    />
                  </StaticHeader>
                  <SortableHeader field="date" className="min-w-[90px]">
                    {t("cogs.date")}
                  </SortableHeader>
                  <StaticHeader className="min-w-[88px]">
                    {t("cogs.actions")}
                  </StaticHeader>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                      {t("cogs.empty")}
                    </TableCell>
                  </TableRow>
                ) : (
                  sorted.map((item) => (
                    <TableRow key={item.barcode_norm} className="hover:bg-muted/50">
                      <TableCell
                        className={cn(
                          "z-10 bg-gray-50/95 pl-4 backdrop-blur-sm dark:bg-gray-800/90",
                          PRODUCT_NAME_COLUMN_CLASS
                        )}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <ProductThumbnail
                            imageUrl={item.product_image_url}
                            alt={item.product_name ?? t("product.name")}
                          />
                          <div className="min-w-0 break-words whitespace-normal text-sm">
                            <p className="font-medium text-foreground">
                              {item.product_name ?? "—"}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              SKU: {item.sku ?? "—"}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-center font-mono text-xs">
                        {item.barcode ?? "—"}
                      </TableCell>
                      <TableCell className="text-center font-medium">
                        {formatValue(item.price)}
                      </TableCell>
                      <TableCell className="text-center font-medium">
                        {formatValue(item.lk_cogs)}
                      </TableCell>
                      <TableCell className="text-center font-medium">
                        {item.actual_cogs != null ? formatValue(item.actual_cogs) : "—"}
                      </TableCell>
                      <TableCell className="text-center font-medium">
                        {formatValue(item.unit_margin)}
                      </TableCell>
                      <TableCell className="text-center">
                        {renderCalculationBadge(item.calculation_source)}
                      </TableCell>
                      <TableCell className="text-center text-sm">
                        {formatDate(item.date)}
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-0.5">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openEdit(item)}
                            aria-label={t("cogs.edit")}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openHistory(item)}
                            aria-label={t("cogs.history")}
                          >
                            <History className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      <Dialog
        open={!!editItem}
        onOpenChange={(open) => {
          if (!open) {
            setEditItem(null);
            setEditValue("");
            setEditEffectiveFrom("");
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t("cogs.editTitle")}</DialogTitle>
          </DialogHeader>
          {editItem && (
            <div className="space-y-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{editItem.product_name ?? "—"}</p>
                <p className="text-sm text-muted-foreground">
                  {t("table.article")}: {editItem.sku ?? "—"}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="actual-cogs">{t("cogs.actual")}</Label>
                <Input
                  id="actual-cogs"
                  inputMode="decimal"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  placeholder={t("cogs.actualPlaceholder")}
                />
                <p className="text-xs text-muted-foreground">
                  {t("cogs.lkUzum")}: {formatValue(editItem.lk_cogs)}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="effective-from">{t("cogs.effectiveFrom")}</Label>
                <Input
                  id="effective-from"
                  type="date"
                  value={editEffectiveFrom}
                  onChange={(e) => setEditEffectiveFrom(e.target.value)}
                  className="h-9"
                />
                <p className="text-xs text-muted-foreground">
                  {t("cogs.firstSaleDate")}:{" "}
                  {editItem.first_sale_date ? formatDate(editItem.first_sale_date) : "—"}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setEditItem(null)}>
              {t("action.cancel")}
            </Button>
            <Button type="button" onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? t("cogs.saving") : t("expense.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!historyItem} onOpenChange={(open) => !open && setHistoryItem(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{t("cogs.historyTitle")}</DialogTitle>
          </DialogHeader>
          {historyItem && (
            <div className="space-y-4">
              <div className="space-y-1 text-sm">
                <p className="font-medium text-foreground">
                  {historyData?.product_name ?? historyItem.product_name ?? "—"}
                </p>
                <p className="text-muted-foreground">
                  {t("table.article")}: {historyData?.sku ?? historyItem.sku ?? "—"}
                </p>
              </div>

              {historyLoading ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {t("cogs.loading")}
                </p>
              ) : !historyData?.items?.length ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {t("cogs.historyEmpty")}
                </p>
              ) : (
                <div className="rounded-lg border border-border overflow-hidden">
                  <div
                    className="overflow-y-auto overscroll-contain [scrollbar-gutter:stable]"
                    style={{ maxHeight: `calc(2.5rem + ${HISTORY_VISIBLE_ROWS} * 2.5rem)` }}
                  >
                    <Table wrapperClassName="overflow-visible">
                      <TableHeader className="sticky top-0 z-10 bg-background [&_tr]:border-b">
                        <TableRow>
                          <TableHead className="h-10 py-2 text-center">
                            {t("cogs.historyPeriod")}
                          </TableHead>
                          <TableHead className="h-10 py-2 text-center">
                            {t("cogs.historyCogs")}
                          </TableHead>
                          <TableHead className="h-10 py-2 text-center">
                            {t("cogs.calculation")}
                          </TableHead>
                          <TableHead className="h-10 py-2 w-12" />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {historyData.items.map((entry, idx) => (
                          <TableRow key={`${entry.period_from}-${entry.period_to}-${idx}`}>
                            <TableCell className="py-2 text-center text-sm whitespace-nowrap">
                              {formatPeriod(entry.period_from, entry.period_to)}
                            </TableCell>
                            <TableCell className="py-2 text-center font-medium">
                              {formatValue(entry.cogs)}
                            </TableCell>
                            <TableCell className="py-2 text-center">
                              {renderCalculationBadge(entry.calculation_source)}
                            </TableCell>
                            <TableCell className="py-2 text-center">
                              {entry.can_delete || entry.calculation_source === "profiboard" ? (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                  disabled={deleteHistoryMutation.isPending}
                                  onClick={() =>
                                    deleteHistoryMutation.mutate(
                                      entry.effective_from ?? entry.period_from
                                    )
                                  }
                                  aria-label={t("cogs.historyDelete")}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              ) : null}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={templateAppliedDialogOpen} onOpenChange={setTemplateAppliedDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("cogs.templateAppliedTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("cogs.templateAppliedMessage")
                .replace("{count}", String(templateAppliedCount))
                .replace("{date}", yearStartLabel)}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction>{t("cogs.templateAppliedOk")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
