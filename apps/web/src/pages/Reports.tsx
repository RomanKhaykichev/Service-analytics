import { FileText, Download, Share2, Clock, CheckCircle, Loader2, Plus } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const templates = [
  {
    id: 1,
    title: "Еженедельный обзор",
    description: "Ключевые метрики продаж и трендов за неделю",
    icon: "📊",
  },
  {
    id: 2,
    title: "Цены и маржинальность",
    description: "Анализ цен, маржи и рентабельности товаров",
    icon: "💰",
  },
  {
    id: 3,
    title: "Отзывы и качество",
    description: "Сводка отзывов, рейтингов и качества товаров",
    icon: "⭐",
  },
  {
    id: 4,
    title: "Конкурентный анализ",
    description: "Сравнение с конкурентами по ценам и продажам",
    icon: "🎯",
  },
];

const reportHistory = [
  {
    id: 1,
    name: "Еженедельный обзор — 20.12.2024",
    template: "Еженедельный обзор",
    status: "ready",
    date: "20 дек 2024",
    author: "Александр Н.",
    format: "PDF",
  },
  {
    id: 2,
    name: "Анализ цен — Электроника",
    template: "Цены и маржинальность",
    status: "ready",
    date: "18 дек 2024",
    author: "Александр Н.",
    format: "XLSX",
  },
  {
    id: 3,
    name: "Отзывы за ноябрь",
    template: "Отзывы и качество",
    status: "processing",
    date: "15 дек 2024",
    author: "Система",
    format: "PDF",
  },
  {
    id: 4,
    name: "Конкуренты Q4 2024",
    template: "Конкурентный анализ",
    status: "ready",
    date: "10 дек 2024",
    author: "Александр Н.",
    format: "PDF",
  },
];

const Reports = () => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ready":
        return (
          <Badge className="bg-success/10 text-success hover:bg-success/20">
            <CheckCircle className="w-3 h-3 mr-1" />
            Готов
          </Badge>
        );
      case "processing":
        return (
          <Badge className="bg-warning/10 text-warning hover:bg-warning/20">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            Генерация
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Отчёты" }]} />

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Отчёты</h1>
          <p className="text-muted-foreground">
            Генерация и управление аналитическими отчётами
          </p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Создать отчёт
        </Button>
      </div>

      {/* Templates */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-foreground mb-4">
          Шаблоны отчётов
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {templates.map((template) => (
            <Card
              key={template.id}
              className="cursor-pointer hover:border-primary/30 hover:shadow-md transition-all group"
            >
              <CardHeader className="pb-2">
                <div className="text-3xl mb-2">{template.icon}</div>
                <CardTitle className="text-base group-hover:text-primary transition-colors">
                  {template.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{template.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Report History */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">
            История отчётов
          </h2>
          <Button variant="ghost" size="sm">
            Все отчёты
          </Button>
        </div>

        <div className="space-y-3">
          {reportHistory.map((report) => (
            <div
              key={report.id}
              className="kpi-card flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start sm:items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium text-foreground">{report.name}</h3>
                  <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-muted-foreground">
                    <span>{report.template}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {report.date}
                    </span>
                    <span>•</span>
                    <span>{report.author}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 ml-14 sm:ml-0">
                {getStatusBadge(report.status)}
                <Badge variant="secondary">{report.format}</Badge>
                {report.status === "ready" && (
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon">
                      <Download className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <Share2 className="w-4 h-4" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </MainLayout>
  );
};

export default Reports;
