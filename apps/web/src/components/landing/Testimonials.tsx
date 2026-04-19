import { Star } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Container } from "./Container";

const testimonialsRu = [
  {
    quote:
      "Пользуюсь Profiboard уже несколько месяцев — это один из самых полезных сервисов для работы с UZUM. Раньше считал все в екселе, но понял что многое не учитывал. Очень удобно анализировать продажи, видеть реальные цифры по прибыли и понимать, какие товары действительно зарабатывают. Однозначно рекомендую.",
    author: "Манукин Илья",
    avatar: "/testimonial-1.png",
  },
  {
    quote:
      "Отличный сервис для системной работы с маркетплейсом. помогает контролировать продажи, расходы на рекламу и хранение в одном месте. Был в шоке когда увидел что реклама съедает всю прибыль с товара) Видно, что продукт сделан продавцами для продавцов. Сервис действительно помогает расти и зарабатывать больше.",
    author: "Клещев Владислав",
    avatar: "/testimonial-2.png",
  },
  {
    quote:
      "Удобно отслеживать остатки и вовремя отгружать товар. Можно посмотреть весь свой заработок за год. Рекомендую новичкам, очень облегчает контроль своего магазина. Спасибо.",
    author: "Хаметов Аброр",
    avatar: "/testimonial-3.png",
  },
  {
    quote:
      "Был реально удивлён, когда через Profiboard увидел, сколько денег у меня уходило на штрафы от UZUM. Раньше даже не обращал на это внимания — казалось, мелочи, а в итоге за месяц набегала очень приличная сумма. После оптимизации штрафы сократились в разы, а прибыль заметно выросла. полностью себя окупает.",
    author: "Азизов Бобур",
    avatar: "/testimonial-4.png",
  },
];

const testimonialsUz = [
  {
    quote:
      "Profiboard’dan bir necha oydan beri foydalanayapman — UZUM bilan ishlash uchun eng foydali servislarning biri. Avval hammasini excell’da hisoblab, ko‘p narsani inobatga olmayotganimni bilmasdim. Bu yerda savdolarni tahlil qilish, foyda bo‘yicha real raqamlarni ko‘rish va qaysi tovarlar haqiqatan ham daromad keltirayotganini tushunish juda qulay. Albatta tavsiya qilaman.",
    author: "Manukin Ilya",
    avatar: "/testimonial-1.png",
  },
  {
    quote:
      "Marketpleys bilan tizimli ishlash uchun zo‘r servis. Savdolarni, reklama va saqlash xarajatlarini bir joyda nazorat qilish mumkin. Reklama butun foydani yeb qo‘yayotganini ko‘rganda hayron bo‘ldim) Mahsulot sotuvchilari tomonidan sotuvchilar uchun yaratilgani bilinib turibdi. Servis haqiqatan ham o‘sishga va ko‘proq daromad olishga yordam beradi.",
    author: "Kleshchev Vladislav",
    avatar: "/testimonial-2.png",
  },
  {
    quote:
      "Qoldiqlarni kuzatish va vaqtida tovar jo‘natish juda qulay. Butun yil davomida qancha daromad topganingizni ko‘rish mumkin. Yangi boshlayotganlarga tavsiya qilaman, do‘konni nazorat qilishni ancha yengillashtiradi. Rahmat.",
    author: "Xametov Abror",
    avatar: "/testimonial-3.png",
  },
  {
    quote:
      "Profiboard orqali UZUM jarimalariga qancha pul ketayotganini ko‘rib haqiqatan ham hayron bo‘ldim. Avval bunga unchalik e’tibor bermasdim — mayda narsa deb o‘ylardim, lekin oy yakunida juda katta summa yig‘ilib qolarkan. Optimallashtirgandan keyin jarimalar bir necha bor kamaydi, foyda esa sezilarli darajada oshdi. Servis o‘zini to‘liq oqlaydi.",
    author: "Azizov Bobur",
    avatar: "/testimonial-4.png",
  },
];

/** Рейтинг 5 звёзд */
function StarRating() {
  return (
    <div className="flex gap-0.5 text-amber-500" aria-label="Рейтинг 5 из 5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star key={i} className="h-4 w-4 fill-current" />
      ))}
    </div>
  );
}

/** Секция отзывов: 2×2 сетка, звёзды, цитата, аватар, имя. */
export function Testimonials() {
  const { language } = useLanguage();
  const testimonials = language === "uz" ? testimonialsUz : testimonialsRu;
  const heading =
    language === "uz"
      ? "FOYDALANUVCHILAR PROFIBOARD HAQIDA"
      : "Что говорят о PROFiboard";

  return (
    <section
      id="testimonials"
      className="py-16 sm:py-20 md:py-24 bg-muted/30"
      data-nosnippet
    >
      <Container>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground tracking-tight text-center mb-10 md:mb-12 lg:mb-14">
          {heading}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 max-w-5xl mx-auto">
          {testimonials.map((t, i) => (
            <div
              key={i}
              className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col"
            >
              <StarRating />
              <p className="mt-4 text-sm sm:text-base text-foreground leading-relaxed flex-1">
                {t.quote}
              </p>
              <div className="mt-6 flex flex-col items-center gap-2">
                <img
                  src={t.avatar}
                  alt=""
                  className="h-16 w-16 rounded-full object-cover border-2 border-border"
                />
                <span className="text-sm font-medium text-foreground">{t.author}</span>
              </div>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
