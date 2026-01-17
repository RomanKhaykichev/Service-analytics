import { Upload, FileText, Bell, TrendingUp, Package, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

const actions = [
  {
    icon: Upload,
    label: "Импорт товаров",
    description: "Загрузить CSV/XLSX",
    color: "bg-primary-light text-primary",
  },
  {
    icon: FileText,
    label: "Создать отчёт",
    description: "Генератор отчётов",
    color: "bg-accent-light text-accent",
  },
  {
    icon: Bell,
    label: "Мониторинг",
    description: "Настроить оповещения",
    color: "bg-warning/10 text-warning",
  },
  {
    icon: TrendingUp,
    label: "Анализ трендов",
    description: "Найти возможности",
    color: "bg-success/10 text-success",
  },
];

export function QuickActions() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-fade-in">
      {actions.map((action) => (
        <button
          key={action.label}
          className="kpi-card text-left hover:border-primary/30 group transition-all"
        >
          <div
            className={`w-10 h-10 rounded-lg ${action.color} flex items-center justify-center mb-3 transition-transform group-hover:scale-110`}
          >
            <action.icon className="w-5 h-5" />
          </div>
          <p className="font-medium text-foreground text-sm">{action.label}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{action.description}</p>
        </button>
      ))}
    </div>
  );
}
