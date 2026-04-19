import { FileText, CircleDollarSign, Package } from "lucide-react";
import dashboardPreview from "@/assets/landing/dashboard-preview.png";
import { Container } from "./Container";
import { SectionTitle } from "./SectionTitle";
import { useLanguage } from "@/contexts/LanguageContext";

const featuresRu = [
  {
    icon: FileText,
    title: "Кажется, что продажи есть, но прибыли нет?",
    description:
      "Сервис дает полный срез ваших финансовых показателей по месяцам/неделям/дням. Следите за своими продажами, оптимизируйте траты для получения большей прибыли.",
  },
  {
    icon: CircleDollarSign,
    title: "Не понимаете, сколько съедает БУСТ В ТОП?",
    description:
      "Недельные рекламные кампании выглядят недорогими. Но в месяц это внушительная сумма. Анализируйте вашу рекламу и оптимизируйте в случае больших затрат.",
  },
  {
    icon: Package,
    title: "Товар лежит и переходит на платное хранение?",
    description:
      "Контролируйте изменение габаритной группы ваших товаров, а так же переход на платное хранение. Отгружайте столько товара, чтобы не переплачивать за склад.",
  },
];

const featuresUz = [
  {
    icon: FileText,
    title: "Savdo bor, lekin foyda yo‘qdek tuyuladimi?",
    description:
      "Servis sizning moliyaviy ko‘rsatkichlaringiz bo‘yicha oy/hafta/kun kesimidagi to‘liq tahlilni ko‘rsatadi. Savdolarni kuzating, ko‘proq foyda olish uchun xarajatlarni optimallashtiring.",
  },
  {
    icon: CircleDollarSign,
    title: "BUST TOP reklama qancha yeyayotganini tushunmayapsizmi?",
    description:
      "Haftalik reklama kampaniyalari arzondek ko‘rinadi, lekin oy oxirida bu jiddiy summa bo‘lishi mumkin. Reklamangizni tahlil qiling va ortiqcha xarajatlar bo‘lsa, optimallashtiring.",
  },
  {
    icon: Package,
    title: "Mahsulot omborda yotib, pullik saqlashga o‘tib ketayaptimi?",
    description:
      "Tovarlariingiz gabarit guruhi o‘zgarishini va pullik saqlashga o‘tishini nazorat qiling. Ombor uchun ortiqcha to‘lamaslik uchun kerakli miqdorda tovar jo‘nating.",
  },
];

/** Секция #features: карточки, два крупных двухстрочных заголовка (одинаковая типографика). */
const headlineTitleClass = "text-3xl sm:text-4xl md:text-5xl";
const headlineSubtitleClass =
  "mt-1 text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-foreground tracking-tight max-w-2xl mx-auto";

export function Features() {
  const { language } = useLanguage();
  const features = language === "uz" ? featuresUz : featuresRu;
  const headlineTop =
    language === "uz"
      ? "Kerak bo‘lgan hamma narsa"
      : "Всё необходимое для контроля бизнеса";
  const headlineBottom = language === "uz" ? "bitta joyda" : "в одном месте";
  const innerHeadline =
    language === "uz" ? "Ichki analitika sizning LK" : "Внутренняя аналитика вашего ЛК";
  const topParagraph =
    language === "uz"
      ? "Biz marketpleyslardagi savdolaringizni tahlil qilish uchun moslashuvchan jadvallar va filtrlar bilan o‘nlab qulay hisobotlarni tayyorlab qo‘yganmiz."
      : "Простые и удобные отчеты, позволяющие решить любые задачи по анализу ваших продаж на маркетплейсе UZUM с настраиваемыми таблицами и гибкими фильтрами.";
  const bottomParagraph =
    language === "uz"
      ? "Savdolaringizni va foydangizni barcha xarajatlarni hisobga olgan holda kuzatib boring. Tovar yetkazib berishni savdo dinamikasi va qoldiqlarni inobatga olgan holda rejalashtiring."
      : "Отслеживайте свои продажи и прибыль с учетом всех издержек. Планируйте поставки товаров с учетом динамики продаж и остатков.";

  return (
    <section id="features" className="pt-16 sm:pt-20 md:pt-24 pb-8 sm:pb-10 md:pb-12 bg-white">
      <Container>
        <SectionTitle
          title={headlineTop}
          subtitle={headlineBottom}
          titleClassName={headlineTitleClass}
          subtitleClassName={headlineSubtitleClass}
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {features.map((item, i) => (
            <div
              key={i}
              className="rounded-xl border border-border bg-card p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col items-center text-center"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-sky-100 text-sky-600 shrink-0">
                <item.icon className="h-6 w-6" />
              </div>
              <h3 className="mt-4 text-base sm:text-lg font-semibold text-foreground">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
        <SectionTitle
          className="mt-12 sm:mt-14 md:mt-16 mb-0"
          title={innerHeadline}
          titleClassName={headlineTitleClass}
        />
        <p className="mt-6 sm:mt-8 text-center text-muted-foreground max-w-5xl mx-auto text-base sm:text-lg">
          {topParagraph}
        </p>
        <div className="mt-8 sm:mt-10 flex justify-center max-w-5xl w-full mx-auto overflow-hidden rounded-2xl border-2 border-[#7F7F7F]">
          <img
            src={dashboardPreview}
            alt="Мои продажи на UZUM — сводка дашборда"
            className="w-full rounded-2xl"
          />
        </div>
        <p className="mt-8 sm:mt-10 text-center font-bold text-foreground max-w-5xl mx-auto text-lg sm:text-xl md:text-2xl leading-relaxed">
          {bottomParagraph}
        </p>
      </Container>
    </section>
  );
}
