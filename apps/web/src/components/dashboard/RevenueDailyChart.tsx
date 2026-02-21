import { useState, useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot, LabelList } from "recharts";
import { MessageSquarePlus, MessageSquare } from "lucide-react";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { CalendarIcon } from "lucide-react";
import { formatNumber, formatCurrency, formatMoneyNoDecimals } from "@/lib/formatters";
import { useLanguage } from "@/contexts/LanguageContext";
interface ChartComment {
  id: string;
  date: string;
  comment: string;
}
interface RevenueDailyChartProps {
  productName?: string;
  showCommentButton?: boolean;
  /** Скрыть средний чек; на карточке товара показываем Заказы, Возвраты, Выручка, Прибыль по формулам из блоков Продажи и Финансы */
  hideAvgCheck?: boolean;
  data?: Array<{
    date: string;
    revenue?: number | null;
    orders?: number | null;
    avgCheck?: number | null;
    returns?: number | null;
    profit?: number | null;
  }>;
}
export function RevenueDailyChart({
  productName = "Товар",
  showCommentButton = false,
  hideAvgCheck = false,
  data
}: RevenueDailyChartProps) {
  const { t } = useLanguage();
  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());
  const [comments, setComments] = useState<ChartComment[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [commentText, setCommentText] = useState("");
  const [editingComment, setEditingComment] = useState<ChartComment | null>(null);

  const chartData = data && data.length > 0 ? data : [];
  const hasData = chartData.length > 0;

  // Fixed orders Y-axis configuration: domain [0, 48], ticks with step 6
  const ordersTicks = [0, 6, 12, 18, 24, 30, 36, 42, 48];

  const hasProductMetrics = hideAvgCheck;

  // Prepare data with clamped orders/returns for display (max 48) but keep original for tooltip
  const data2 = useMemo(() => {
    return chartData.map((point) => {
      const ordersOriginal = Number(point.orders ?? 0);
      const ordersClamped = Math.min(ordersOriginal, 48);
      const returnsOriginal = Number(point.returns ?? 0);
      const returnsClamped = Math.min(returnsOriginal, 48);
      const revenueValue = Number(point.revenue ?? 0);
      const profitValue = Math.round(Number(point.profit ?? 0));
      const avgCheckValue = Number(point.avgCheck ?? (point as any).averageCheck ?? 0);
      return {
        ...point,
        ordersOriginal,
        ordersClamped,
        returnsOriginal,
        returnsClamped,
        revenueValue,
        profitValue,
        avgCheckValue,
      };
    });
  }, [chartData]);

  // Custom label for orders > 48
  const renderOrdersLabel = (props: any) => {
    const { payload, x, y } = props;
    if (!payload || payload.ordersOriginal === undefined) return null;
    if (payload.ordersOriginal > 48) {
      return (
        <text
          x={x}
          y={y - 8}
          fill="hsl(var(--destructive))"
          fontSize={10}
          fontWeight="bold"
          textAnchor="middle"
        >
          48+
        </text>
      );
    }
    return null;
  };

  const handleLegendClick = (dataKey: string) => {
    setHiddenLines(prev => {
      const next = new Set(prev);
      if (next.has(dataKey)) {
        next.delete(dataKey);
      } else {
        next.add(dataKey);
      }
      return next;
    });
  };
  const openNewCommentDialog = () => {
    setEditingComment(null);
    setSelectedDate(undefined);
    setCommentText("");
    setIsDialogOpen(true);
  };
  const openEditCommentDialog = (comment: ChartComment) => {
    setEditingComment(comment);
    // Parse the date from dd.MM format
    const [day, month] = comment.date.split(".");
    const year = new Date().getFullYear();
    setSelectedDate(new Date(year, parseInt(month) - 1, parseInt(day)));
    setCommentText(comment.comment);
    setIsDialogOpen(true);
  };
  const handleSave = () => {
    if (!selectedDate || !commentText.trim()) return;
    const dateStr = format(selectedDate, "dd.MM");
    if (editingComment) {
      setComments(prev => prev.map(c => c.id === editingComment.id ? {
        ...c,
        date: dateStr,
        comment: commentText.trim()
      } : c));
    } else {
      const newComment: ChartComment = {
        id: Date.now().toString(),
        date: dateStr,
        comment: commentText.trim()
      };
      setComments(prev => [...prev, newComment]);
    }
    setIsDialogOpen(false);
    setSelectedDate(undefined);
    setCommentText("");
    setEditingComment(null);
  };
  const handleDelete = () => {
    if (editingComment) {
      setComments(prev => prev.filter(c => c.id !== editingComment.id));
    }
    setIsDialogOpen(false);
    setSelectedDate(undefined);
    setCommentText("");
    setEditingComment(null);
  };
  const renderLegend = (props: any) => {
    const {
      payload
    } = props;
    return <div className="flex justify-center gap-4 mt-2">
        {payload.map((entry: any) => <button key={entry.dataKey} onClick={() => handleLegendClick(entry.dataKey)} className={`flex items-center gap-2 px-2 py-1 rounded transition-opacity ${hiddenLines.has(entry.dataKey) ? "opacity-40" : "opacity-100"}`}>
            <span className="w-3 h-3 rounded-full" style={{
          backgroundColor: entry.color
        }} />
            <span className="text-xs text-muted-foreground">
              {entry.value || entry.dataKey}
            </span>
          </button>)}
      </div>;
  };

  // Find data point for a comment date
  const getDataPointForDate = (dateStr: string) => {
    return data2.find(d => d.date === dateStr);
  };

  // Custom component for comment markers
  const CommentMarker = ({
    cx,
    cy,
    comment
  }: {
    cx: number;
    cy: number;
    comment: ChartComment;
  }) => {
    return <g onClick={e => {
      e.stopPropagation();
      openEditCommentDialog(comment);
    }} style={{
      cursor: "pointer"
    }}>
        <circle cx={cx} cy={cy} r={12} fill="hsl(var(--primary))" />
        <MessageSquare x={cx - 6} y={cy - 6} width={12} height={12} fill="hsl(var(--primary-foreground))" />
      </g>;
  };
  return <div className="bg-card rounded-xl p-5 border border-border shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-foreground">{t('chart.salesByDay')}</h3>
        {showCommentButton && (
          <Button
            variant="outline"
            size="sm"
            onClick={openNewCommentDialog}
            className="flex items-center gap-2"
          >
            <MessageSquarePlus className="h-4 w-4" />
            {t('chart.addComment')}
          </Button>
        )}
      </div>
      
      <div className="h-72">
        {hasData ? (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data2}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{
            fill: "hsl(var(--muted-foreground))",
            fontSize: 12
          }} axisLine={{
            stroke: "hsl(var(--border))"
          }} />
            <YAxis 
              yAxisId="orders" 
              domain={[0, 48]}
              ticks={ordersTicks}
              interval={0}
              allowDecimals={false}
              tick={{
                fill: "hsl(var(--muted-foreground))",
                fontSize: 12
              }} 
              axisLine={{
                stroke: "hsl(var(--border))"
              }} 
              label={{
                value: t('chart.ordersPcs'),
                angle: -90,
                position: "insideLeft",
                style: {
                  fill: "hsl(var(--muted-foreground))",
                  fontSize: 11
                }
              }} 
            />
            <YAxis 
              yAxisId="revenue" 
              orientation="right" 
              tick={{
                fill: "hsl(var(--muted-foreground))",
                fontSize: 12
              }} 
              axisLine={{
                stroke: "hsl(var(--border))"
              }} 
              tickFormatter={(value) => (value / 1_000_000).toFixed(1)}
              label={{
                value: t('chart.revenueMlnSum'),
                angle: 90,
                position: "insideRight",
                style: {
                  fill: "hsl(var(--muted-foreground))",
                  fontSize: 11
                }
              }} 
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px"
              }}
              formatter={(value: number | null | undefined, name: string, entry: any) => {
                if (value === null || value === undefined || Number.isNaN(value)) {
                  return ["—", name];
                }
                if (entry?.dataKey === "revenueValue") {
                  const payload = entry?.payload;
                  const v = payload?.revenueValue ?? value;
                  return [`${v.toLocaleString("ru-RU")} сум`, t('summary.finance.revenue')];
                }
                if (entry?.dataKey === "profitValue") {
                  const payload = entry?.payload;
                  const v = payload?.profitValue ?? value;
                  return [`${Math.round(v).toLocaleString("ru-RU")} сум`, t('summary.finance.profit')];
                }
                if (entry?.dataKey === "ordersClamped") {
                  const payload = entry?.payload;
                  const ordersOriginal = payload?.ordersOriginal ?? value;
                  const pcs = t('common.pieces');
                  if (ordersOriginal > 48) return [`48+ (${t('chart.reallyOrders')}: ${ordersOriginal} ${pcs})`, t('summary.sales.orders')];
                  return [`${ordersOriginal} ${pcs}`, t('summary.sales.orders')];
                }
                if (entry?.dataKey === "returnsClamped") {
                  const payload = entry?.payload;
                  const returnsOriginal = payload?.returnsOriginal ?? value;
                  const pcs = t('common.pieces');
                  if (returnsOriginal > 48) return [`48+ (${t('chart.reallyOrders')}: ${returnsOriginal} ${pcs})`, t('summary.sales.returns')];
                  return [`${returnsOriginal} ${pcs}`, t('summary.sales.returns')];
                }
                return [value, name];
              }} 
            />
            <Legend content={renderLegend} />
            <Line 
              yAxisId="orders" 
              type="monotone" 
              dataKey="ordersClamped"
              name={t('summary.sales.orders')}
              stroke="hsl(var(--chart-4))" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
              hide={hiddenLines.has("ordersClamped")}
            >
              <LabelList content={renderOrdersLabel} />
            </Line>
            {hasProductMetrics && (
            <Line 
              yAxisId="orders" 
              type="monotone" 
              dataKey="returnsClamped"
              name={t('summary.sales.returns')}
              stroke="hsl(var(--chart-2))" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
              hide={hiddenLines.has("returnsClamped")} 
            />
            )}
            <Line 
              yAxisId="revenue" 
              type="monotone" 
              dataKey="revenueValue"
              name={t('summary.finance.revenue')}
              stroke="hsl(var(--destructive))" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
              hide={hiddenLines.has("revenueValue")} 
            />
            {/* Прибыль показывается всегда, когда есть данные (для сводки и карточки товара) */}
            {chartData.some(p => p.profit !== undefined && p.profit !== null) && (
            <Line 
              yAxisId="revenue" 
              type="monotone" 
              dataKey="profitValue"
              name={t('summary.finance.profit')}
              stroke="hsl(var(--chart-3))" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4 }} 
              hide={hiddenLines.has("profitValue")} 
            />
            )}
            {/* Render comment markers */}
            {comments.map(comment => {
            const dataPoint = getDataPointForDate(comment.date);
            if (dataPoint) {
              return <ReferenceDot key={comment.id} x={comment.date} y={dataPoint.revenueValue ?? 0} yAxisId="revenue" r={0} label={({
                viewBox
              }) => {
                const {
                  x,
                  y
                } = viewBox as {
                  x: number;
                  y: number;
                };
                return <g onClick={e => {
                  e.stopPropagation();
                  openEditCommentDialog(comment);
                }} style={{
                  cursor: "pointer"
                }}>
                          <circle cx={x} cy={y - 20} r={10} fill="hsl(var(--primary))" />
                          <text x={x} y={y - 16} textAnchor="middle" fill="hsl(var(--primary-foreground))" fontSize={10}>
                            💬
                          </text>
                        </g>;
              }} />;
            }
            return null;
          })}
          </LineChart>
        </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            {t('chart.noData')}
          </div>
        )}
      </div>

      {/* Comment Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{productName}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">{t('chart.date')}</p>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className={cn("w-full justify-start text-left font-normal", !selectedDate && "text-muted-foreground")}>
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {selectedDate ? format(selectedDate, "PPP", {
                    locale: ru
                  }) : <span>{t('chart.selectDate')}</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} initialFocus className="p-3 pointer-events-auto" />
                </PopoverContent>
              </Popover>
            </div>
            
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                {t('chart.comment')} ({commentText.length}/200)
              </p>
              <Textarea placeholder={t('product.commentPlaceholder')} value={commentText} onChange={e => {
              if (e.target.value.length <= 200) {
                setCommentText(e.target.value);
              }
            }} className="min-h-[100px] resize-none" maxLength={200} />
            </div>
          </div>
          
          <DialogFooter className="flex justify-between w-full">
            <Button variant="destructive" onClick={handleDelete}>
              {t('chart.delete')}
            </Button>
            <Button onClick={handleSave} disabled={!selectedDate || !commentText.trim()}>
              {t('chart.done')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>;
}