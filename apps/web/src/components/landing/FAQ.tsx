import { Container } from "./Container";

const faqItems = [
  {
    question: "Как это работает?",
    answer:
      "Вы загружаете 4 ваших основных отчета с начала года и получаете данные по вашей прибыли и тратам в удобном виде, с возможностью фильтрации и анализа. Мы подготовили общий отчет чтобы вы следили за динамикой от месяца к месяцу. Если хотите обновить данные, просто загрузите новые отчеты с начала года и посмотрите как изменилась ситуация.",
  },
  {
    question: "У вас есть поддержка?",
    answer:
      "ДА, Наша отзывчивая служба поддержки готова решить практически любые вопросы наших клиентов по запросу в TG или на почту.",
  },
  {
    question: "Насколько безопасно загружать свои отчеты?",
    answer:
      "Конфиденциальность наш приоритет номер один. Мы не разглашаем персональные данные из личных кабинетов наших клиентов, а так же храним их в обезличенном виде. что закреплено в договоре-оферте. После каждой новой загрузки, ваши прошлые данные удаляются. PROFiboard авторизованный сервис аналитики и полностью безопасен. Данные переданные через выгрузки аналогичны данным переданым по API.",
  },
  {
    question: "Как давно вы работаете?",
    answer:
      "Сервис PROFiboard первоначально был разработан для внутреннего использования в 2023 году. Публичная версия сервиса появилась в 2026 году. За три года работы мы увидели что многие селлеры испытывают сложность с отчетами и решили сделать его публичным. В дальнейшем мы планируем много обновлений, которые помогут продавцу держать «руку на пульсе» и не торговать в убыток. Присоединяйтесь!",
  },
];

/** Один блок вопрос-ответ */
function FAQBlock({ question, answer }: { question: string; answer: string }) {
  return (
    <div className="space-y-2 text-left">
      <h3 className="text-base sm:text-lg font-bold text-foreground">{question}</h3>
      <p className="text-sm sm:text-base text-foreground font-normal leading-relaxed">
        {answer}
      </p>
    </div>
  );
}

/** Порядок в сетке 2×2: строка 1 — (0, 2), строка 2 — (1, 3), чтобы «У вас есть поддержка?» и «Как давно вы работаете?» были на одной линии */
const faqGridOrder = [0, 2, 1, 3];

/** Секция «Часто задаваемые вопросы» — сетка 2×2, строки выровнены. */
export function FAQ() {
  return (
    <section id="faq" className="pt-16 sm:pt-20 md:pt-24 pb-8 sm:pb-10 md:pb-12 bg-white">
      <Container>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight text-center mb-10 md:mb-12 lg:mb-14">
          Часто задаваемые вопросы
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-10 md:gap-x-12 md:gap-y-12 max-w-5xl mx-auto text-left items-start">
          {faqGridOrder.map((index) => {
            const item = faqItems[index];
            return (
              <FAQBlock
                key={index}
                question={item.question}
                answer={item.answer}
              />
            );
          })}
        </div>
      </Container>
    </section>
  );
}
