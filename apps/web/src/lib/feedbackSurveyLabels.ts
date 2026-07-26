/** Shared labels for feedback survey (form + admin view). */

export type SurveyAnswers = {
  tenure?: string;
  frequency?: string;
  helpfulness?: string;
  nps?: string;
  analyticsTools?: string[];
  analyticsOther?: string;
  importance?: Record<string, string>;
  otherMetrics?: string;
  sectionsUsed?: string[];
  sectionsUsedOther?: string;
  mostUseful?: string;
  leastUsed?: string;
  sectionsNeeded?: string[];
  sectionsNeededOther?: string;
  ratings?: Record<string, string>;
  onboardingHelp?: string;
  outcomes?: string[];
  outcomesOther?: string;
  timeSaved?: string;
  difficulties?: string[];
  difficultiesOther?: string;
  annoying?: string;
  missing?: string;
  oneChange?: string;
  supportRating?: string;
  continueUsing?: string;
  improveToStay?: string;
  comment?: string;
  clientName?: string;
  clientContact?: string;
};

export const IMPORTANCE_ITEMS = [
  { key: "revenue", label: "Выручка и заказы" },
  { key: "profit", label: "Прибыль / маржа после всех расходов" },
  { key: "ads", label: "Реклама и её эффективность" },
  { key: "logistics", label: "Логистика и хранение" },
  { key: "returns", label: "Возвраты" },
  { key: "stock", label: "Остатки и поставки" },
  { key: "unit", label: "Юнит-экономика по товарам" },
  { key: "periods", label: "Сравнение периодов (неделя/месяц)" },
  { key: "shops", label: "Несколько магазинов в одном окне" },
  { key: "manualExpenses", label: "Ручные расходы (зарплата, аренда, упаковка и т.п.)" },
] as const;

export const RATING_ITEMS = [
  { key: "ui", label: "Удобство интерфейса" },
  { key: "metrics", label: "Понятность метрик и цифр" },
  { key: "speed", label: "Скорость работы сервиса" },
  { key: "upload", label: "Удобство загрузки отчётов" },
  { key: "trust", label: "Точность / доверие к данным" },
  { key: "support", label: "Помощь и поддержка" },
  { key: "onboarding", label: "Обучение / онбординг" },
] as const;

const MAPS = {
  tenure: {
    lt1m: "меньше месяца",
    "1to3m": "1–3 месяца",
    "3to6m": "3–6 месяцев",
    gt6m: "более 6 месяцев",
  },
  frequency: {
    daily: "каждый день",
    fewWeek: "несколько раз в неделю",
    weekly: "раз в неделю",
    rare: "реже",
  },
  analyticsTools: {
    excel: "Excel / Google Sheets",
    cabinet: "отчёты кабинета маркетплейса",
    other: "другой сервис",
    none: "ничего системного",
  },
  sectionsUsed: {
    summary: "Сводка",
    daily: "Дневная динамика",
    products: "Товары",
    expenses: "Расходы",
    shipment: "Поставки / отгрузки",
    monthly: "Месячная сводка",
    other: "другое",
  },
  sectionsNeeded: {
    summary: "Сводка / дашборд",
    daily: "Дневная динамика",
    products: "Аналитика по товарам",
    expenses: "Расходы",
    shipment: "Поставки / отгрузки",
    monthly: "Месячная сводка",
    training: "Обучение / помощь",
    other: "другое",
  },
  onboardingHelp: {
    yes: "да, нужна",
    partial: "частично",
    no: "нет, разберёмся сами",
  },
  outcomes: {
    faster: "быстрее вижу ключевые цифры",
    profit: "лучше понимаю прибыль",
    unprofitable: "проще находить убыточные товары",
    lessExcel: "меньше времени на Excel / ручные отчёты",
    expenses: "удобнее контролировать расходы",
    shipment: "проще принимать решения по поставкам",
    none: "пока заметных изменений нет",
    other: "другое",
  },
  timeSaved: {
    none: "почти ничего",
    lt1: "до 1 часа",
    "1to3": "1–3 часа",
    "3to5": "3–5 часов",
    gt5: "более 5 часов",
  },
  difficulties: {
    metrics: "непонятно, как считать / читать метрики",
    upload: "неудобная загрузка отчётов",
    mismatch: "данные расходятся с кабинетом маркетплейса",
    slow: "медленно работает",
    filters: "не хватает нужных отчётов / фильтров",
    hard: "сложно разобраться без помощи",
    other: "другое",
    none: "особых проблем не было",
  },
  continueUsing: {
    yes: "да, точно",
    likelyYes: "скорее да",
    unsure: "пока не уверен(а)",
    likelyNo: "скорее нет",
    no: "нет",
  },
} as const;

function mapOne(dict: Record<string, string>, value?: string) {
  if (!value) return "—";
  return dict[value] ?? value;
}

function mapMany(
  dict: Record<string, string>,
  values?: string[],
  otherText?: string,
  otherKey = "other"
) {
  if (!values?.length) return "—";
  return values
    .map((v) => {
      const base = dict[v] ?? v;
      if (v === otherKey && otherText?.trim()) return `${base}: ${otherText.trim()}`;
      return base;
    })
    .join("; ");
}

function textOrDash(value?: string) {
  const v = (value || "").trim();
  return v || "—";
}

export type SurveyViewSection = {
  title: string;
  rows: { question: string; answer: string }[];
};

export function buildSurveyViewSections(raw: Record<string, unknown>): SurveyViewSection[] {
  const a = raw as SurveyAnswers;
  const importance = a.importance || {};
  const ratings = a.ratings || {};

  return [
    {
      title: "1. Общий опыт",
      rows: [
        { question: "Как давно пользуетесь сервисом?", answer: mapOne(MAPS.tenure, a.tenure) },
        { question: "Как часто заходите в сервис?", answer: mapOne(MAPS.frequency, a.frequency) },
        { question: "Насколько сервис помогает в работе? (1–10)", answer: textOrDash(a.helpfulness) },
        { question: "Готовность рекомендовать / NPS (0–10)", answer: textOrDash(a.nps) },
      ],
    },
    {
      title: "2. Чем ещё пользуетесь для аналитики",
      rows: [
        {
          question: "Чем пользуетесь сейчас для аналитики?",
          answer: mapMany(MAPS.analyticsTools, a.analyticsTools, a.analyticsOther),
        },
      ],
    },
    {
      title: "3. Что важнее всего контролировать",
      rows: [
        ...IMPORTANCE_ITEMS.map((item) => ({
          question: item.label,
          answer: textOrDash(importance[item.key]),
        })),
        { question: "Какие ещё метрики обязательны?", answer: textOrDash(a.otherMetrics) },
      ],
    },
    {
      title: "4. Что используете в сервисе",
      rows: [
        {
          question: "Какими разделами пользуетесь чаще всего?",
          answer: mapMany(MAPS.sectionsUsed, a.sectionsUsed, a.sectionsUsedOther),
        },
        { question: "Самый полезный раздел", answer: textOrDash(a.mostUseful) },
        { question: "Почти не используете и почему", answer: textOrDash(a.leastUsed) },
        {
          question: "Какие разделы нужны в первую очередь?",
          answer: mapMany(MAPS.sectionsNeeded, a.sectionsNeeded, a.sectionsNeededOther),
        },
      ],
    },
    {
      title: "5. Оценка по блокам",
      rows: RATING_ITEMS.map((item) => ({
        question: item.label,
        answer: textOrDash(ratings[item.key]),
      })),
    },
    {
      title: "6. Онбординг и помощь",
      rows: [
        {
          question: "Нужна ли помощь с онбордингом?",
          answer: mapOne(MAPS.onboardingHelp, a.onboardingHelp),
        },
      ],
    },
    {
      title: "7. Результат для бизнеса",
      rows: [
        {
          question: "Что изменилось после начала работы с сервисом?",
          answer: mapMany(MAPS.outcomes, a.outcomes, a.outcomesOther),
        },
        {
          question: "Сколько времени в неделю экономите?",
          answer: mapOne(MAPS.timeSaved, a.timeSaved),
        },
      ],
    },
    {
      title: "8. Проблемы и улучшения",
      rows: [
        {
          question: "С какими сложностями сталкивались?",
          answer: mapMany(MAPS.difficulties, a.difficulties, a.difficultiesOther),
        },
        { question: "Что раздражает или мешает?", answer: textOrDash(a.annoying) },
        { question: "Чего не хватает в первую очередь?", answer: textOrDash(a.missing) },
        { question: "Одну вещь изменить — что бы это было?", answer: textOrDash(a.oneChange) },
      ],
    },
    {
      title: "9. Поддержка и дальше",
      rows: [
        { question: "Оценка поддержки (1–5)", answer: textOrDash(a.supportRating) },
        {
          question: "Планируете продолжать пользоваться?",
          answer: mapOne(MAPS.continueUsing, a.continueUsing),
        },
        {
          question: "Что должно улучшиться, чтобы остались / рекомендовали?",
          answer: textOrDash(a.improveToStay),
        },
        { question: "Комментарий", answer: textOrDash(a.comment) },
        { question: "Контакт (Telegram / email / телефон)", answer: textOrDash(a.clientContact) },
      ],
    },
  ];
}
