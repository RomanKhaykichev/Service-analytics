import { useState, type FormEvent } from "react";
import { HelpCircle, MessageCircle, ArrowLeft } from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLanguage } from "@/contexts/LanguageContext";
import { apiPost } from "@/lib/api";

const faqItemsRu = [
  {
    question: "Как подключить API в PROFiboard?",
    answer:
      "Создаёте API-ключ в кабинете Uzum Seller и вставляете его в раздел «Настройки → API-токен» в ScaleUp. Пошаговая инструкция со скриншотами — во вкладке «Инструкции». Занимает пару минут.",
  },
  {
    question: "Безопасно ли передавать API-ключ?",
    answer:
      "Да. Ключ — это не логин и пароль от кабинета. Он даёт сервису доступ только к данным магазина (заказы, расходы, товары, остатки, накладные). Ключ не дает возможности корректировать данные в ЛК, только собирать для анализа. Контроль остаётся за вами: ключ в любой момент можно отозвать в кабинете Uzum, и доступ сразу прекратится.",
  },
  {
    question: "Можно ли доверять вашим данным?",
    answer:
      "Информация тянется напрямую из официального API маркетплейса вашего ЛК, без ручного ввода.",
  },
  {
    question: "Чем пробный тариф отличается от платного?",
    answer:
      "На пробном тарифе число магазинов ограничено тарифом, а в расчётах учитываются данные не глубже последних 60 дней из загруженных отчётов. Чтобы снять ограничения, оформите платный план в меню аккаунта («Продлить тариф»).",
  },
  {
    question: "Где посмотреть видеоинструкции?",
    answer:
      "В меню «Помощь» выберите «Видео-уроки» или откройте раздел «Обучение»: ролики по всем вкладкам сервиса.",
  },
];

const faqItemsUz = [
  {
    question: "PROFiboardga API qanday ulash mumkin?",
    answer:
      "Uzum Seller kabinetida API-kalit yaratasiz va uni ScaleUp’dagi «Sozlamalar → API-token» bo‘limiga joylashtirasiz. Skrinshotli bosqichma-bosqich yo‘riqnoma — «Yo‘riqnomalar» bo‘limida. Bir necha daqiqa vaqt oladi.",
  },
  {
    question: "Sizga API-kalit berish xavfsizmi?",
    answer:
      "Ha. Kalit — bu kabinetdan login va parol emas. U xizmatga faqat do‘kon ma’lumotlariga (buyurtmalar, xarajatlar, tovarlar, qoldiqlar, yuk xatlari) rasmiy Uzum API orqali kirish huquqini beradi — u orqali shaxsiy kabinetingizga kirib bo‘lmaydi. Nazorat sizda qoladi: kalitni istalgan vaqtda Uzum kabinetida bekor qilish mumkin, va kirish darhol to‘xtaydi.",
  },
  {
    question: "Ma'lumotlar qayerdan olinadi - ularga ishonsa bo'ladimi?",
    answer:
      "Hammasi to‘g‘ridan-to‘g‘ri marketpleysning rasmiy API’sidan olinadi, qo‘lda kiritishsiz.",
  },
  {
    question: "Sinov tarifi to‘lovli tarifdan qanday farq qiladi?",
    answer:
      "Sinovda do‘konlar soni tarifga qarab cheklangan, hisoblarda esa yuklangan hisobotlardan oxirgi 60 kun maʼlumoti hisobga olinadi. Cheklovlarni yechish uchun akkaunt menyusida «Tarif rejani yangilash» orqali pullik rejani rasmiylashtiring.",
  },
  {
    question: "Video qo‘llanmalarni qayerdan ko‘rish mumkin?",
    answer:
      "«Yordam» menyusida «Video-darsliklar»ni tanlang yoki «O‘qitish» bo‘limini oching: xizmatning barcha bo‘limlari bo‘yicha rolliklar.",
  },
];

const Support = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "contact" ? "contact" : "help";
  const faqItems = language === "uz" ? faqItemsUz : faqItemsRu;

  const [subject, setSubject] = useState("");
  const [priority, setPriority] = useState("medium");
  const [category, setCategory] = useState("technical");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const resetForm = () => {
    setSubject("");
    setPriority("medium");
    setCategory("technical");
    setDescription("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const sub = subject.trim();
    const desc = description.trim();
    if (!sub) {
      toast.error(t("support.subjectRequired"));
      return;
    }
    if (!desc) {
      toast.error(t("support.descriptionRequired"));
      return;
    }
    setSubmitting(true);
    try {
      await apiPost<{ id: string; created_at: string }>("/api/support/tickets", {
        subject: sub,
        priority,
        category,
        description: desc,
      });
      toast.success(t("support.ticketSent"), { description: t("support.ticketSentDesc") });
      resetForm();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(msg || t("support.ticketError"));
    } finally {
      setSubmitting(false);
    }
  };

  const setTab = (value: string) => {
    if (value === "contact") {
      setSearchParams({ tab: "contact" });
    } else {
      setSearchParams({});
    }
  };

  return (
    <MainLayout>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-foreground">{t("support.title")}</h1>
          <p className="text-muted-foreground mt-1 max-w-3xl">{t("support.subtitle")}</p>
        </div>
        <Button
          type="button"
          variant="default"
          size="sm"
          className="shrink-0 self-end sm:self-start gap-2"
          onClick={() => navigate("/")}
        >
          <ArrowLeft className="w-4 h-4" />
          {t("learning.back")}
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="space-y-6">
        <TabsList className="bg-muted/50">
          <TabsTrigger value="help" className="gap-2">
            <HelpCircle className="w-4 h-4" />
            {t("support.tabHelp")}
          </TabsTrigger>
          <TabsTrigger value="contact" className="gap-2">
            <MessageCircle className="w-4 h-4" />
            {t("support.tabContact")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="help">
          <div className="chart-container max-w-3xl">
            <h3 className="font-semibold text-foreground mb-4">{t("support.faqHeading")}</h3>
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
        </TabsContent>

        <TabsContent value="contact">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,36rem)_minmax(220px,300px)] lg:items-stretch xl:gap-10">
            <Card className="min-w-0 max-w-2xl h-full flex flex-col border-border shadow-sm min-h-0">
              <CardHeader className="pb-4">
                <CardTitle className="text-base font-semibold">{t("support.contactFormTitle")}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col pt-0 min-h-0">
            <form className="flex flex-1 flex-col gap-4 min-h-0" onSubmit={handleSubmit}>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="subject">{t("support.fieldSubject")}</Label>
                  <Input
                    id="subject"
                    placeholder={t("support.fieldSubjectPh")}
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    disabled={submitting}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="priority">{t("support.fieldPriority")}</Label>
                  <Select value={priority} onValueChange={setPriority} disabled={submitting}>
                    <SelectTrigger id="priority">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">{t("support.priorityLow")}</SelectItem>
                      <SelectItem value="medium">{t("support.priorityMedium")}</SelectItem>
                      <SelectItem value="high">{t("support.priorityHigh")}</SelectItem>
                      <SelectItem value="critical">{t("support.priorityCritical")}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">{t("support.fieldCategory")}</Label>
                <Select value={category} onValueChange={setCategory} disabled={submitting}>
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="technical">{t("support.catTechnical")}</SelectItem>
                    <SelectItem value="billing">{t("support.catBilling")}</SelectItem>
                    <SelectItem value="feature">{t("support.catFeature")}</SelectItem>
                    <SelectItem value="data">{t("support.catData")}</SelectItem>
                    <SelectItem value="other">{t("support.catOther")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">{t("support.fieldDescription")}</Label>
                <Textarea
                  id="description"
                  placeholder={t("support.fieldDescriptionPh")}
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={submitting}
                />
              </div>

              <div className="mt-auto flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={resetForm} disabled={submitting}>
                  {t("support.cancel")}
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? t("support.sending") : t("support.submitTicket")}
                </Button>
              </div>
            </form>
              </CardContent>
            </Card>

            <aside className="min-w-0 h-full flex flex-col min-h-0">
              <Card className="h-full min-h-0 flex flex-col overflow-hidden border-border shadow-sm">
                <CardHeader className="pb-2 shrink-0">
                  <CardTitle className="text-base font-semibold">{t("support.viaTelegramHeading")}</CardTitle>
                  <p className="text-sm text-muted-foreground font-normal leading-snug">
                    {t("support.viaTelegramHint")}
                  </p>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col items-center justify-center gap-3 pt-0 pb-6 min-h-0">
                  <a
                    href="https://t.me/PROFI_BOARD"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full max-w-[280px] rounded-xl overflow-hidden ring-1 ring-border/70 bg-card transition-opacity hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <img
                      src="/images/telegram-qr-profiboard.png"
                      alt={t("support.telegramQrAlt")}
                      className="w-full h-auto object-contain"
                      width={280}
                      height={280}
                      loading="lazy"
                    />
                  </a>
                </CardContent>
              </Card>
            </aside>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
};

export default Support;
