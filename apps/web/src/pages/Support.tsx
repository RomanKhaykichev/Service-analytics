import { Search, HelpCircle, FileText, MessageCircle, CheckCircle, Clock, AlertCircle, ExternalLink } from "lucide-react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Breadcrumb } from "@/components/shared/Breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const faqItems = [
  {
    question: "Как подключить UZUM API?",
    answer:
      "Перейдите в Настройки → Интеграции и введите ваш API ключ от UZUM Marketplace. После подключения данные начнут синхронизироваться автоматически.",
  },
  {
    question: "Как часто обновляются данные?",
    answer:
      "Данные о продажах и заказах обновляются каждые 15 минут. Данные о ценах конкурентов — каждый час. Отзывы — раз в сутки.",
  },
  {
    question: "Можно ли экспортировать данные в Excel?",
    answer:
      "Да, вы можете экспортировать любые таблицы и отчёты в форматах CSV и XLSX. Нажмите кнопку 'Экспорт' в правом верхнем углу любой таблицы.",
  },
  {
    question: "Как настроить уведомления о ценах?",
    answer:
      "Перейдите в Настройки → Уведомления и установите пороговые значения для изменения цен. Вы получите уведомление при превышении порога.",
  },
  {
    question: "Поддерживается ли мобильная версия?",
    answer:
      "Да, платформа полностью адаптирована для мобильных устройств. Вы можете использовать все функции с телефона или планшета.",
  },
];

const guides = [
  { title: "Начало работы", description: "Базовое руководство по платформе", icon: "🚀" },
  { title: "Анализ продаж", description: "Как читать графики и метрики", icon: "📊" },
  { title: "Работа с отчётами", description: "Создание и экспорт отчётов", icon: "📄" },
  { title: "Мониторинг конкурентов", description: "Настройка отслеживания", icon: "🎯" },
];

const systemStatus = {
  overall: "operational",
  uptime: "99.98%",
  lastIncident: "15 дней назад",
  services: [
    { name: "API", status: "operational" },
    { name: "Дашборд", status: "operational" },
    { name: "Синхронизация данных", status: "operational" },
    { name: "Отчёты", status: "operational" },
  ],
};

const Support = () => {
  return (
    <MainLayout>
      <Breadcrumb items={[{ label: "Поддержка" }]} />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Центр поддержки</h1>
        <p className="text-muted-foreground">
          Ответы на вопросы и помощь по работе с платформой
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-8 max-w-xl">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <Input
          placeholder="Поиск в справке..."
          className="pl-12 h-12 text-base bg-card"
        />
      </div>

      <Tabs defaultValue="help" className="space-y-6">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="help" className="gap-2">
            <HelpCircle className="w-4 h-4" />
            Справка
          </TabsTrigger>
          <TabsTrigger value="contact" className="gap-2">
            <MessageCircle className="w-4 h-4" />
            Связаться
          </TabsTrigger>
          <TabsTrigger value="status" className="gap-2">
            <CheckCircle className="w-4 h-4" />
            Статус
          </TabsTrigger>
        </TabsList>

        {/* Help Tab */}
        <TabsContent value="help">
          <div className="grid lg:grid-cols-3 gap-6">
            {/* FAQ */}
            <div className="lg:col-span-2 chart-container">
              <h3 className="font-semibold text-foreground mb-4">
                Частые вопросы
              </h3>
              <Accordion type="single" collapsible className="space-y-2">
                {faqItems.map((item, index) => (
                  <AccordionItem
                    key={index}
                    value={`item-${index}`}
                    className="border border-border rounded-lg px-4"
                  >
                    <AccordionTrigger className="text-left hover:no-underline py-4">
                      {item.question}
                    </AccordionTrigger>
                    <AccordionContent className="text-muted-foreground pb-4">
                      {item.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>

            {/* Guides */}
            <div className="chart-container">
              <h3 className="font-semibold text-foreground mb-4">Руководства</h3>
              <div className="space-y-3">
                {guides.map((guide, index) => (
                  <button
                    key={index}
                    className="w-full p-3 rounded-lg border border-border bg-muted/30 hover:bg-muted/50 transition-colors text-left flex items-start gap-3"
                  >
                    <span className="text-2xl">{guide.icon}</span>
                    <div>
                      <p className="font-medium text-foreground">{guide.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {guide.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
              <Button variant="outline" className="w-full mt-4">
                Все руководства
                <ExternalLink className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Contact Tab */}
        <TabsContent value="contact">
          <div className="max-w-2xl chart-container">
            <h3 className="font-semibold text-foreground mb-4">
              Создать тикет
            </h3>
            <form className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="subject">Тема</Label>
                  <Input id="subject" placeholder="Опишите проблему кратко" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="priority">Приоритет</Label>
                  <Select defaultValue="medium">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Низкий</SelectItem>
                      <SelectItem value="medium">Средний</SelectItem>
                      <SelectItem value="high">Высокий</SelectItem>
                      <SelectItem value="critical">Критический</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Категория</Label>
                <Select defaultValue="technical">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="technical">Техническая проблема</SelectItem>
                    <SelectItem value="billing">Оплата и подписка</SelectItem>
                    <SelectItem value="feature">Запрос функции</SelectItem>
                    <SelectItem value="data">Данные и отчёты</SelectItem>
                    <SelectItem value="other">Другое</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Описание</Label>
                <Textarea
                  id="description"
                  placeholder="Подробно опишите вашу проблему или вопрос..."
                  rows={5}
                />
              </div>

              <div className="space-y-2">
                <Label>Вложения</Label>
                <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
                  <p className="text-muted-foreground">
                    Перетащите файлы сюда или{" "}
                    <button className="text-primary underline">выберите</button>
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    PNG, JPG, PDF до 10MB
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button variant="outline">Отмена</Button>
                <Button>Отправить тикет</Button>
              </div>
            </form>
          </div>
        </TabsContent>

        {/* Status Tab */}
        <TabsContent value="status">
          <div className="chart-container max-w-2xl">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-success animate-pulse" />
                <h3 className="font-semibold text-foreground">
                  Все системы работают нормально
                </h3>
              </div>
              <Badge className="bg-success/10 text-success">Uptime {systemStatus.uptime}</Badge>
            </div>

            <div className="space-y-3 mb-6">
              {systemStatus.services.map((service, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border border-border"
                >
                  <span className="font-medium text-foreground">{service.name}</span>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-success" />
                    <span className="text-sm text-success">Работает</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 rounded-lg bg-muted/30 border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">
                  Последний инцидент
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {systemStatus.lastIncident} — Плановое обслуживание (30 минут)
              </p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
};

export default Support;
