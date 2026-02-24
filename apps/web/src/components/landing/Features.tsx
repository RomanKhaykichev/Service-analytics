import { FileText, CircleDollarSign, Package } from "lucide-react";
import { Container } from "./Container";
import { SectionTitle } from "./SectionTitle";

const features = [
  {
    icon: FileText,
    title: "кажется что продажи есть, но прибыли нет?",
    description:
      "Сервис дает полный срез ваших финансовых показателей по месяцам/неделям/дням. Следите за своими продажами, оптимизируйте траты для получения большей прибыли.",
  },
  {
    icon: CircleDollarSign,
    title: "не понимаете сколько съедает БУСТ В ТОП?",
    description:
      "Недельные рекламные компании выглядят не дорогими. Но в месяц это внушительные сумма. Анализируйте вашу рекламу и оптимизируйте в случае больших затрат.",
  },
  {
    icon: Package,
    title: "товар лежит и переходит на платное хранение?",
    description:
      "Контролируйте изменение габаритной группы ваших товаров, а так же переход на платное хранение. Отгружайте столько товара, чтобы не переплачивать за склад.",
  },
];

/** Секция «Возможности»: 3 карточки сверху, заголовок и подзаголовок снизу (как раньше). */
export function Features() {
  return (
    <section id="features" className="pt-16 sm:pt-20 md:pt-24 pb-8 sm:pb-10 md:pb-12 bg-white">
      <Container>
        <SectionTitle
          title="Возможности"
          subtitle="Всё необходимое для контроля бизнеса в одном сервисе"
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
          title="внутренняя аналитика"
          subtitle="вашего личного кабинета"
          titleClassName="text-3xl sm:text-4xl md:text-5xl"
          subtitleClassName="mt-1 text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-foreground tracking-tight max-w-2xl mx-auto"
        />
        <p className="mt-6 sm:mt-8 text-center text-muted-foreground max-w-5xl mx-auto text-base sm:text-lg">
          Мы подготовили десятки удобных отчетов, позволяющих решить любые задачи по анализу ваших
          продаж на маркетплейсах с настраиваемыми таблицами и гибкими фильтрами.
        </p>
        <div className="mt-8 sm:mt-10 flex justify-center max-w-5xl w-full mx-auto overflow-hidden rounded-2xl border-2 border-[#7F7F7F]">
          <img
            src="/dashboard-preview.png"
            alt="Мои продажи на UZUM — сводка дашборда"
            className="w-full rounded-2xl"
          />
        </div>
        <p className="mt-8 sm:mt-10 text-center font-bold text-foreground max-w-5xl mx-auto text-lg sm:text-xl md:text-2xl leading-relaxed">
          Отслеживайте свои продажи и прибыль с учетом всех издержек.
          <br />
          Планируйте поставки товаров с учетом динамики продаж и остатков.
        </p>
      </Container>
    </section>
  );
}
