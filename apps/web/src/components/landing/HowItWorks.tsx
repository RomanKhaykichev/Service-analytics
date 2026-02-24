import { Container } from "./Container";
import { SectionTitle } from "./SectionTitle";

const steps = [
  { step: 1, title: "Подключите магазин", text: "Авторизуйтесь и привяжите свой магазин к сервису." },
  { step: 2, title: "Загрузите данные", text: "Импортируйте заказы, товары и расходы за нужный период." },
  { step: 3, title: "Смотрите отчёты", text: "Дашборды и отчёты обновляются автоматически." },
];

/** Секция «Как это работает». TODO: шаги и визуал — из Figma. */
export function HowItWorks() {
  return (
    <section id="how-it-works" className="pt-8 sm:pt-10 md:pt-12 pb-16 sm:pb-20 md:pb-24 bg-white scroll-mt-20 sm:scroll-mt-24">
      <Container>
        <SectionTitle
          title="Как это работает"
          subtitle="Три простых шага до первых отчётов"
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-10">
          {steps.map((item, i) => (
            <div key={item.step} className="relative text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold text-lg">
                {item.step}
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.text}</p>
              {i < steps.length - 1 && (
                <div className="hidden md:block absolute top-6 left-[calc(50%+2rem)] w-[calc(100%-4rem)] h-0.5 bg-border" aria-hidden />
              )}
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
