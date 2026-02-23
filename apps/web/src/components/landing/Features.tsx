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
    <section id="features" className="py-16 sm:py-20 md:py-24 bg-white">
      <Container>
        <SectionTitle
          title="Возможности"
          subtitle="Всё необходимое для контроля бизнеса в одном сервисе"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {features.map((item, i) => (
            <div
              key={i}
              className="rounded-xl border border-border bg-card p-6 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-sky-100 text-sky-600">
                <item.icon className="h-6 w-6" />
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
        <SectionTitle
          className="mt-12 sm:mt-14 md:mt-16 mb-0"
          title="внутренняя аналитика"
          subtitle="вашего личного кабинета"
          subtitleClassName="mt-1 text-2xl sm:text-3xl md:text-4xl font-bold text-foreground tracking-tight max-w-2xl mx-auto"
        />
      </Container>
    </section>
  );
}
