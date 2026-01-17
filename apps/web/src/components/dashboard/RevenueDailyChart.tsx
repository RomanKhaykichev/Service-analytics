import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot } from "recharts";
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
interface ChartComment {
  id: string;
  date: string;
  comment: string;
}
interface RevenueDailyChartProps {
  productName?: string;
  showCommentButton?: boolean;
  data?: Array<{
    date: string;
    revenue: number;
    orders?: number;
    avgCheck?: number;
  }>;
}
const defaultData = [{
  date: "01.12",
  avgCheck: 350,
  orders: 220,
  revenue: 77000
}, {
  date: "02.12",
  avgCheck: 320,
  orders: 245,
  revenue: 78400
}, {
  date: "03.12",
  avgCheck: 280,
  orders: 210,
  revenue: 58800
}, {
  date: "04.12",
  avgCheck: 340,
  orders: 280,
  revenue: 95200
}, {
  date: "05.12",
  avgCheck: 360,
  orders: 320,
  revenue: 115200
}, {
  date: "06.12",
  avgCheck: 310,
  orders: 290,
  revenue: 89900
}, {
  date: "07.12",
  avgCheck: 290,
  orders: 250,
  revenue: 72500
}, {
  date: "08.12",
  avgCheck: 330,
  orders: 310,
  revenue: 102300
}, {
  date: "09.12",
  avgCheck: 350,
  orders: 340,
  revenue: 119000
}, {
  date: "10.12",
  avgCheck: 320,
  orders: 280,
  revenue: 89600
}, {
  date: "11.12",
  avgCheck: 340,
  orders: 350,
  revenue: 119000
}, {
  date: "12.12",
  avgCheck: 380,
  orders: 380,
  revenue: 144400
}, {
  date: "13.12",
  avgCheck: 400,
  orders: 410,
  revenue: 164000
}];
export function RevenueDailyChart({
  productName = "Товар",
  showCommentButton = false,
  data = defaultData
}: RevenueDailyChartProps) {
  const [hiddenLines, setHiddenLines] = useState<Set<string>>(new Set());
  const [comments, setComments] = useState<ChartComment[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [commentText, setCommentText] = useState("");
  const [editingComment, setEditingComment] = useState<ChartComment | null>(null);
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
              {entry.dataKey === "avgCheck" && "Средний чек"}
              {entry.dataKey === "orders" && "Заказы"}
              {entry.dataKey === "revenue" && "Выручка"}
            </span>
          </button>)}
      </div>;
  };

  // Find data point for a comment date
  const getDataPointForDate = (dateStr: string) => {
    return data.find(d => d.date === dateStr);
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
        <h3 className="text-base font-semibold text-foreground">Продажи по дням</h3>
        {showCommentButton && (
          <Button
            variant="outline"
            size="sm"
            onClick={openNewCommentDialog}
            className="flex items-center gap-2"
          >
            <MessageSquarePlus className="h-4 w-4" />
            Добавить комментарий
          </Button>
        )}
      </div>
      
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{
            fill: "hsl(var(--muted-foreground))",
            fontSize: 12
          }} axisLine={{
            stroke: "hsl(var(--border))"
          }} />
            <YAxis yAxisId="left" tick={{
            fill: "hsl(var(--muted-foreground))",
            fontSize: 12
          }} axisLine={{
            stroke: "hsl(var(--border))"
          }} label={{
            value: "Заказы, шт",
            angle: -90,
            position: "insideLeft",
            style: {
              fill: "hsl(var(--muted-foreground))",
              fontSize: 11
            }
          }} />
            <YAxis yAxisId="right" orientation="right" tick={{
            fill: "hsl(var(--muted-foreground))",
            fontSize: 12
          }} axisLine={{
            stroke: "hsl(var(--border))"
          }} tickFormatter={value => `${(value / 1000).toFixed(0)}k`} label={{
            value: "Выручка, ₽",
            angle: 90,
            position: "insideRight",
            style: {
              fill: "hsl(var(--muted-foreground))",
              fontSize: 11
            }
          }} />
            <Tooltip contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "8px"
          }} formatter={(value: number, name: string) => {
            if (name === "revenue") return [`${value.toLocaleString()} ₽`, "Выручка"];
            if (name === "orders") return [value, "Заказы"];
            if (name === "avgCheck") return [`${value} ₽`, "Средний чек"];
            return [value, name];
          }} />
            <Legend content={renderLegend} />
            <Line yAxisId="left" type="monotone" dataKey="avgCheck" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} activeDot={{
            r: 4
          }} hide={hiddenLines.has("avgCheck")} />
            <Line yAxisId="left" type="monotone" dataKey="orders" stroke="hsl(var(--chart-4))" strokeWidth={2} dot={false} activeDot={{
            r: 4
          }} hide={hiddenLines.has("orders")} />
            <Line yAxisId="right" type="monotone" dataKey="revenue" stroke="hsl(var(--destructive))" strokeWidth={2} dot={false} activeDot={{
            r: 4
          }} hide={hiddenLines.has("revenue")} />
            {/* Render comment markers */}
            {comments.map(comment => {
            const dataPoint = getDataPointForDate(comment.date);
            if (dataPoint) {
              return <ReferenceDot key={comment.id} x={comment.date} y={dataPoint.revenue} yAxisId="right" r={0} label={({
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
      </div>

      {/* Comment Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{productName}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Дата</p>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className={cn("w-full justify-start text-left font-normal", !selectedDate && "text-muted-foreground")}>
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {selectedDate ? format(selectedDate, "PPP", {
                    locale: ru
                  }) : <span>Выберите дату</span>}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar mode="single" selected={selectedDate} onSelect={setSelectedDate} initialFocus className="p-3 pointer-events-auto" />
                </PopoverContent>
              </Popover>
            </div>
            
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                Комментарий ({commentText.length}/200)
              </p>
              <Textarea placeholder="Введите комментарий..." value={commentText} onChange={e => {
              if (e.target.value.length <= 200) {
                setCommentText(e.target.value);
              }
            }} className="min-h-[100px] resize-none" maxLength={200} />
            </div>
          </div>
          
          <DialogFooter className="flex justify-between w-full">
            <Button variant="destructive" onClick={handleDelete}>
              Удалить
            </Button>
            <Button onClick={handleSave} disabled={!selectedDate || !commentText.trim()}>
              Готово
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>;
}