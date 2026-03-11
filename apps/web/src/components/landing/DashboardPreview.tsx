import {
  Upload,
  Info,
  ChevronDown,
  Calendar,
  ShoppingCart,
  Truck,
  RotateCcw,
  Receipt,
  TrendingUp,
  TrendingDown,
  Package,
  Gem,
  Box,
  AlertCircle,
  Tag,
} from "lucide-react";
import { Container } from "./Container";
import { useLanguage } from "@/contexts/LanguageContext";

const tabsRu = ["Сводка", "По дням", "Товары", "Доп. расходы", "Отгрузка", "Помесячно"];
const tabsUz = ["Hisobot", "Kunlar bo‘yicha", "Tovarlar", "Qo‘shimcha xarajatlar", "Yuklab jo‘natish", "Oylik"];

/**
 * Блок-превью дашборда после «Возможности»: текст, карточка с отчётами и подпись.
 */
export function DashboardPreview() {
  const { language } = useLanguage();
  const tabs = language === "uz" ? tabsUz : tabsRu;
  const topText =
    language === "uz"
      ? "Marketpleyslardagi savdolaringizni tahlil qilish bo‘yicha istalgan vazifani hal qilishga yordam beradigan, moslashuvchan jadvallar va filtrlar bilan o‘nlab qulay hisobotlarni tayyorlab qo‘yganmiz."
      : "Мы подготовили десятки удобных отчетов, позволяющих решить любые задачи по анализу ваших продаж на маркетплейсах с настраиваемыми таблицами и гибкими фильтрами.";
  const bottomText =
    language === "uz"
      ? "Savdo va foydani barcha xarajatlarni inobatga olgan holda kuzatib boring. Tovar yetkazib berishni savdo dinamikasi va qoldiqlarni hisobga olgan holda rejalashtiring."
      : "Отслеживайте свои продажи и прибыль с учетом всех издержек. Планируйте поставки товаров с учетом динамики продаж и остатков.";

  return (
    <section className="py-16 sm:py-20 md:py-24 bg-zinc-100">
      <Container>
        <p className="text-center text-base sm:text-lg text-muted-foreground max-w-3xl mx-auto mb-8 md:mb-10">
          {topText}
        </p>

        <div className="rounded-2xl bg-white shadow-lg border border-border overflow-hidden max-w-6xl mx-auto">
          {/* Шапка дашборда */}
          <div className="p-4 sm:p-5 border-b border-border bg-white">
            <div className="flex flex-wrap items-center gap-3 gap-y-3">
              <span className="text-sm text-muted-foreground">
                {language === "uz" ? "Mening savdolarim" : "Мои продажи на"}
              </span>
              <span className="inline-flex items-center px-3 py-1 rounded-full bg-violet-600 text-white text-sm font-medium">
                UZUM
              </span>
              <span className="text-sm text-muted-foreground">
                {language === "uz" ? "01.01.2026 dan 09.02.2026 gacha" : "от 01.01.2026 до 09.02.2026"}
              </span>
              <span className="hidden sm:inline text-sm text-muted-foreground mx-2">·</span>
              <span className="text-sm font-medium">
                {language === "uz" ? "2026 yil umumiy tushumi" : "Накопительная выручка 2026"}
              </span>
            </div>
            <div className="mt-3 flex flex-col sm:flex-row sm:items-center gap-2">
              <div className="flex-1 h-2 bg-zinc-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 rounded-full"
                  style={{ width: "11.3%" }}
                />
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                113 млн / 1 млрд
              </span>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-600 text-white text-sm font-medium"
              >
                <Upload className="h-4 w-4" />
                Загрузить отчеты
              </button>
              <button type="button" className="p-1.5 rounded-md hover:bg-zinc-100 text-muted-foreground">
                <Info className="h-4 w-4" />
              </button>
              <span className="text-sm text-muted-foreground ml-2">Dev User</span>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">до 15.02.2025</span>
              <span className="flex-1" />
              <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-green-600 text-green-700 text-sm font-medium">
                {language === "uz" ? "Barcha do‘konlar" : "Все магазины"} <ChevronDown className="h-4 w-4" />
              </button>
              <button className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-sm">
                <Calendar className="h-4 w-4" /> 10.01.2026 - 09.02.2026
              </button>
            </div>
          </div>

          {/* Табы */}
          <div className="flex flex-wrap gap-1 px-4 sm:px-5 py-2 border-b border-border bg-white">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                type="button"
                className={`px-3 py-2 text-sm font-medium rounded-md ${
                  i === 0
                    ? "text-violet-600 border-b-2 border-violet-600 -mb-[1px]"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Контент: метрики */}
          <div className="p-4 sm:p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* ПРОДАЖИ */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                {language === "uz" ? "Savdolar" : "Продажи"}
              </h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <ShoppingCart className="h-3.5 w-3.5" /> Заказы <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">856 шт / 136 417 030</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Package className="h-3.5 w-3.5" /> В обработке <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">238 шт / 37 470 366</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Truck className="h-3.5 w-3.5" /> Выкупы <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">357 шт / 57 793 510</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <RotateCcw className="h-3.5 w-3.5" /> Возвраты <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums text-red-600">261 шт / -41 153 154</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    % {language === "uz" ? "Qaytarishlar foizi" : "Процент возврата"} <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">30.5%</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Receipt className="h-3.5 w-3.5" /> {language === "uz" ? "O‘rtacha chek" : "Средний чек"}
                  </span>
                  <span className="font-medium tabular-nums">160 107</span>
                </li>
              </ul>
              <p className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
                {language === "uz" ? "Kunlik savdolar" : "Продажи по дням"}
              </p>
            </div>

            {/* ФИНАНСЫ */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                {language === "uz" ? "Moliya" : "Финансы"}
              </h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    $ {language === "uz" ? "Tushum" : "Выручка"} <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">95 263 876</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">Расходы</span>
                  <span className="font-medium tabular-nums">79 734 912</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">Прибыль</span>
                  <span className="font-medium tabular-nums text-green-600">15 528 964</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    Рентабельность продаж <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">16.3%</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    Окупаемость инвестиций <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">19.5%</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <TrendingUp className="h-3.5 w-3.5 text-green-500" />{" "}
                    {language === "uz" ? "Daromad trendlari" : "Тренд выручки"}
                  </span>
                  <span className="font-medium tabular-nums text-green-600">+432.7%</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <TrendingDown className="h-3.5 w-3.5" />{" "}
                    {language === "uz" ? "Yo‘qotilgan tushum" : "Упущенная выручка"}
                  </span>
                  <span className="font-medium tabular-nums">64 839</span>
                </li>
              </ul>
            </div>

            {/* РАСХОДЫ */}
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                {language === "uz" ? "Xarajatlar" : "Расходы"}
              </h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    % {language === "uz" ? "UZUM komissiyasi" : "Комиссия UZUM"} <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">21 665 773</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    {language === "uz" ? "UZUM logistika xizmati" : "Логистика UZUM"}
                  </span>
                  <span className="font-medium tabular-nums">3 036 000</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Tag className="h-3.5 w-3.5" />{" "}
                    {language === "uz" ? "Sotilgan tovarlar tannarxi" : "Себест. прод. тов."}
                  </span>
                  <span className="font-medium tabular-nums">52 575 500</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    {language === "uz" ? "Soliqlar 1 %" : "Налоги 1 %"}
                  </span>
                  <span className="font-medium tabular-nums">952 639</span>
                </li>
                <li className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    {language === "uz" ? "Qo‘shimcha xarajatlar" : "Доп. расходы"}{" "}
                    <Info className="h-3 w-3" />
                  </span>
                  <span className="font-medium tabular-nums">1 505 000</span>
                </li>
              </ul>
              <p className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
                {language === "uz" ? "UZUM xizmatlari" : "Услugi UZUM"}
              </p>
            </div>

            {/* СКЛАД + УСЛУГИ UZUM */}
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  {language === "uz" ? "Ombor" : "Склад"}
                </h4>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <Package className="h-3.5 w-3.5" />{" "}
                      {language === "uz" ? "Ombordagi tovarlar" : "Товаров на складе"}{" "}
                      <Info className="h-3 w-3" />
                    </span>
                    <span className="font-medium tabular-nums">1268 шт</span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <Tag className="h-3.5 w-3.5" />{" "}
                      {language === "uz" ? "Tovar tannarxi" : "Себест. тов."}
                    </span>
                    <span className="font-medium tabular-nums">68 309 960</span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      {language === "uz" ? "Chakana narx" : "Рознич. цена"}{" "}
                      <Info className="h-3 w-3" />
                    </span>
                    <span className="font-medium tabular-nums">134 193 830</span>
                  </li>
                </ul>
              </div>
              <div className="rounded-lg bg-violet-50 p-3 border border-violet-100">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-violet-800 mb-3">
                  {language === "uz" ? "UZUM xizmatlari" : "Услуги UZUM"}
                </h4>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <Box className="h-3.5 w-3.5" />{" "}
                      {language === "uz" ? "UZUM saqlash xizmati" : "Хранение UZUM"}
                    </span>
                    <span className="font-medium tabular-nums">466 250</span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      {language === "uz" ? "UZUM reklama" : "Реклама UZUM"}
                    </span>
                    <span className="font-medium tabular-nums">1 148 648</span>
                  </li>
                  <li className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-muted-foreground">
                      <AlertCircle className="h-3.5 w-3.5" />{" "}
                      {language === "uz" ? "UZUM jarimalar" : "Штрафы UZUM"}
                    </span>
                    <span className="font-medium tabular-nums">0</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-base sm:text-lg text-muted-foreground max-w-3xl mx-auto mt-8 md:mt-10">
          {bottomText}
        </p>
      </Container>
    </section>
  );
}
