import { Container } from "./Container";
import { useLanguage } from "@/contexts/LanguageContext";

const faqItemsRu = [
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

const faqItemsUz = [
  {
    question: "Bu qanday ishlaydi?",
    answer:
      "Yil boshidan boshlab 4 ta asosiy hisobotni yuklaysiz va foyda hamda xarajatlaringiz bo‘yicha qulay ko‘rinishda ma’lumot olasiz, filtrlash va tahlil qilish imkoniyati bilan. Biz umumiy hisobot tayyorlaganmiz, shunda oyma‑oy dinamikani kuzatishingiz mumkin. Agar ma’lumotlarni yangilamoqchi bo‘lsangiz, shunchaki yil boshidan yangi hisobotlarni yuklang va vaziyat qanday o‘zgarganini ko‘ring.",
  },
  {
    question: "Sizlarda qo‘llab-quvvatlash xizmati bormi?",
    answer:
      "HA, bizning javob beruvchi qo‘llab‑quvvatlash xizmati mijozlarimizning deyarli barcha savollarini TG yoki email orqali hal qilishga tayyor.",
  },
  {
    question: "Hisobotlarni yuklash qanchalik xavfsiz?",
    answer:
      "Maxfiylik biz uchun birinchi o‘rinda. Mijozlarimizning shaxsiy kabinetlaridan olingan ma’lumotlarni oshkor qilmaymiz va ularni shaxsga bog‘lanmagan holda saqlaymiz — bu oferta shartnomasida mustahkamlangan. Har bir yangi yuklashdan so‘ng eski ma’lumotlaringiz o‘chiriladi. PROFiboard — avtorizatsiyadan o‘tgan analitika servisi va to‘liq xavfsiz. Yuklash orqali uzatilgan ma’lumotlar API orqali uzatilgan ma’lumotlarga tengdir.",
  },
  {
    question: "Qanchadan beri ishlayapsizlar?",
    answer:
      "PROFiboard dastlab 2023 yilda ichki foydalanish uchun ishlab chiqilgan. Servisning ommaviy versiyasi 2026 yilda paydo bo‘ldi. Uch yil davomida ko‘plab sotuvislar hisobotlar bilan qiynalayotganini ko‘rdik va servisni ommaga ochishga qaror qildik. Kelajakda sotuvchiga “pul’sni ushlab turish” va zarariga savdo qilmaslikka yordam beradigan ko‘plab yangilanishlarni rejalashtirganmiz. Bizga qo‘shiling!",
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
  const { language } = useLanguage();
  const faqItems = language === "uz" ? faqItemsUz : faqItemsRu;
  const heading =
    language === "uz" ? "Ko‘p so‘raladigan savollar" : "Часто задаваемые вопросы";

  return (
    <section id="faq" className="pt-16 sm:pt-20 md:pt-24 pb-8 sm:pb-10 md:pb-12 bg-white">
      <Container>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight text-center mb-10 md:mb-12 lg:mb-14">
          {heading}
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
