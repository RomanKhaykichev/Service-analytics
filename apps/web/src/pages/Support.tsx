import { HelpCircle, MessageCircle, ArrowLeft } from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";
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
import { useLanguage } from "@/contexts/LanguageContext";

const faqItemsRu = [
  {
    question: "Как загрузить отчёты в PROFiboard?",
    answer:
      "Нажмите кнопку загрузки отчётов в шапке панели. Доступны типы: продажи (sells-report), склад (seller-storage-report), затраты (expenses-report), left-out и другие шаблоны. Нужны файлы XLSX в ожидаемом формате — после успешной загрузки данные появятся на сводке и в разделах аналитики.",
  },
  {
    question: "Чем пробный тариф отличается от платного?",
    answer:
      "На пробном тарифе число магазинов ограничено тарифом, а в расчётах учитываются данные не глубже последних 60 дней из загруженных отчётов. Чтобы снять ограничения, оформите платный план в меню аккаунта («Продлить тариф»).",
  },
  {
    question: "Где посмотреть видеоинструкции?",
    answer:
      "В меню «Помощь» выберите «Видео-уроки» или откройте раздел «Обучение»: ролики по импорту отчётов и по вкладке «Сводка».",
  },
  {
    question: "Как сменить язык интерфейса?",
    answer:
      "Нажмите на своё имя в шапке → пункт «Язык» и выберите русский или узбекский.",
  },
  {
    question: "После загрузки файла данные не обновились — что проверить?",
    answer:
      "Обновите страницу. Убедитесь, что файл соответствует типу отчёта и шаблону. Текст ошибки, если загрузка не прошла, показывается в окне загрузки отчётов.",
  },
];

const faqItemsUz = [
  {
    question: "PROFiboardga hisobotlarni qanday yuklash mumkin?",
    answer:
      "Panel sarlavhasidagi hisobot yuklash tugmasini bosing. Mavjud turlar: sotuvlar (sells-report), ombor (seller-storage-report), xarajatlar (expenses-report), left-out va boshqa shablonlar. Kutilgan formatdagi XLSX fayllar kerak — muvaffaqiyatli yuklangandan keyin maʼlumotlar svodka va tahlil bo‘limlarida paydo bo‘ladi.",
  },
  {
    question: "Sinov tarifi to‘lovli tarifdan qanday farq qiladi?",
    answer:
      "Sinovda do‘konlar soni tarifga qarab cheklangan, hisoblarda esa yuklangan hisobotlardan oxirgi 60 kun maʼlumoti hisobga olinadi. Cheklovlarni yechish uchun akkaunt menyusida «Tarif rejani yangilash» orqali pullik rejani rasmiylashtiring.",
  },
  {
    question: "Video qo‘llanmalarni qayerdan ko‘rish mumkin?",
    answer:
      "«Yordam» menyusida «Video-darsliklar»ni tanlang yoki «O‘qitish» bo‘limini oching: hisobot importi va «Svodka» varag‘i bo‘yicha rolliklar.",
  },
  {
    question: "Interfeys tilini qanday almashtirish mumkin?",
    answer:
      "Sarlavhadagi ismingizni bosing → «Til» bandi, keyin rus yoki o‘zbek tilini tanlang.",
  },
  {
    question: "Fayl yuklangandan keyin maʼlumotlar yangilanmadi — nima tekshirish kerak?",
    answer:
      "Sahifani yangilang. Fayl hisobot turi va shablonga mos kelishini tekshiring. Yuklash muvaffaqiyatsiz bo‘lsa, xato matni hisobot yuklash oynasida ko‘rsatiladi.",
  },
];

const Support = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get("tab") === "contact" ? "contact" : "help";
  const faqItems = language === "uz" ? faqItemsUz : faqItemsRu;

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
          <div className="max-w-2xl chart-container">
            <h3 className="font-semibold text-foreground mb-4">{t("support.contactFormTitle")}</h3>
            <form className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="subject">{t("support.fieldSubject")}</Label>
                  <Input id="subject" placeholder={t("support.fieldSubjectPh")} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="priority">{t("support.fieldPriority")}</Label>
                  <Select defaultValue="medium">
                    <SelectTrigger>
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
                <Select defaultValue="technical">
                  <SelectTrigger>
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
                />
              </div>

              <div className="space-y-2">
                <Label>{t("support.fieldAttachments")}</Label>
                <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
                  <p className="text-muted-foreground">
                    {t("support.attachmentsHint")}{" "}
                    <button type="button" className="text-primary underline">
                      {t("support.attachmentsChoose")}
                    </button>
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{t("support.attachmentsLimit")}</p>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <Button type="button" variant="outline">
                  {t("support.cancel")}
                </Button>
                <Button type="button">{t("support.submitTicket")}</Button>
              </div>
            </form>
          </div>
        </TabsContent>
      </Tabs>
    </MainLayout>
  );
};

export default Support;
