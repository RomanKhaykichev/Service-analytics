import { useMemo, useState, type FormEvent } from "react";
import { ArrowLeft, ClipboardList } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLanguage } from "@/contexts/LanguageContext";
import { apiPost } from "@/lib/api";
import { cn } from "@/lib/utils";

type AnswersState = {
  tenure: string;
  frequency: string;
  helpfulness: string;
  nps: string;
  analyticsTools: string[];
  analyticsOther: string;
  importance: Record<string, string>;
  otherMetrics: string;
  sectionsUsed: string[];
  sectionsUsedOther: string;
  mostUseful: string;
  leastUsed: string;
  sectionsNeeded: string[];
  sectionsNeededOther: string;
  ratings: Record<string, string>;
  onboardingHelp: string;
  outcomes: string[];
  outcomesOther: string;
  timeSaved: string;
  difficulties: string[];
  difficultiesOther: string;
  annoying: string;
  missing: string;
  oneChange: string;
  supportRating: string;
  continueUsing: string;
  improveToStay: string;
  comment: string;
  clientContact: string;
};

const INITIAL: AnswersState = {
  tenure: "",
  frequency: "",
  helpfulness: "",
  nps: "",
  analyticsTools: [],
  analyticsOther: "",
  importance: {},
  otherMetrics: "",
  sectionsUsed: [],
  sectionsUsedOther: "",
  mostUseful: "",
  leastUsed: "",
  sectionsNeeded: [],
  sectionsNeededOther: "",
  ratings: {},
  onboardingHelp: "",
  outcomes: [],
  outcomesOther: "",
  timeSaved: "",
  difficulties: [],
  difficultiesOther: "",
  annoying: "",
  missing: "",
  oneChange: "",
  supportRating: "",
  continueUsing: "",
  improveToStay: "",
  comment: "",
  clientContact: "",
};

const IMPORTANCE_KEYS = [
  { key: "revenue", labelRu: "Выручка и заказы", labelUz: "Tushum va buyurtmalar" },
  { key: "profit", labelRu: "Прибыль / маржа после всех расходов", labelUz: "Foyda / barcha xarajatlardan keyin marja" },
  { key: "ads", labelRu: "Реклама и её эффективность", labelUz: "Reklama va uning samaradorligi" },
  { key: "logistics", labelRu: "Логистика и хранение", labelUz: "Logistika va saqlash" },
  { key: "returns", labelRu: "Возвраты", labelUz: "Qaytarishlar" },
  { key: "stock", labelRu: "Остатки и поставки", labelUz: "Qoldiqlar va yetkazib berish" },
  { key: "unit", labelRu: "Юнит-экономика по товарам", labelUz: "Tovarlar bo‘yicha unit-iqtisodiyot" },
  { key: "periods", labelRu: "Сравнение периодов (неделя/месяц)", labelUz: "Davrlarni solishtirish (hafta/oy)" },
  { key: "shops", labelRu: "Несколько магазинов в одном окне", labelUz: "Bir oynada bir nechta do‘kon" },
  { key: "manualExpenses", labelRu: "Ручные расходы (зарплата, аренда, упаковка и т.п.)", labelUz: "Qo‘lda xarajatlar (maosh, ijara, qadoqlash va hokazo)" },
] as const;

const RATING_KEYS = [
  { key: "ui", labelRu: "Удобство интерфейса", labelUz: "Interfeys qulayligi" },
  { key: "metrics", labelRu: "Понятность метрик и цифр", labelUz: "Metrikalar va raqamlarning tushunarliligi" },
  { key: "speed", labelRu: "Скорость работы сервиса", labelUz: "Xizmat tezligi" },
  { key: "upload", labelRu: "Удобство загрузки отчётов", labelUz: "Hisobot yuklash qulayligi" },
  { key: "trust", labelRu: "Точность / доверие к данным", labelUz: "Aniqlik / ma’lumotlarga ishonch" },
  { key: "support", labelRu: "Помощь и поддержка", labelUz: "Yordam va qo‘llab-quvvatlash" },
  { key: "onboarding", labelRu: "Обучение / онбординг", labelUz: "O‘qitish / onboarding" },
] as const;

function toggleMulti(list: string[], value: string, checked: boolean) {
  if (checked) return list.includes(value) ? list : [...list, value];
  return list.filter((v) => v !== value);
}

function ScaleRow({
  value,
  onChange,
  min = 1,
  max = 5,
}: {
  value: string;
  onChange: (v: string) => void;
  min?: number;
  max?: number;
}) {
  const nums = Array.from({ length: max - min + 1 }, (_, i) => String(min + i));
  return (
    <div className="flex flex-wrap gap-2" role="group">
      {nums.map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className={cn(
            "inline-flex h-9 min-w-9 items-center justify-center rounded-md border px-2 text-sm font-medium",
            value === n
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-background hover:bg-muted/60"
          )}
        >
          {n}
        </button>
      ))}
    </div>
  );
}

function OptionList({
  idPrefix,
  options,
  value,
  onChange,
  otherValue,
  onOtherChange,
  otherKey,
}: {
  idPrefix: string;
  options: { value: string; label: string }[];
  value: string[];
  onChange: (next: string[]) => void;
  otherValue?: string;
  onOtherChange?: (v: string) => void;
  otherKey?: string;
}) {
  return (
    <div className="grid gap-2">
      {options.map((opt) => {
        const checked = value.includes(opt.value);
        const isOther = otherKey != null && opt.value === otherKey;
        const id = `${idPrefix}-${opt.value}`;
        return (
          <div
            key={opt.value}
            className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-muted/20 px-3 py-2"
          >
            <Checkbox
              id={id}
              checked={checked}
              onCheckedChange={(c) => onChange(toggleMulti(value, opt.value, c === true))}
            />
            <Label htmlFor={id} className="font-normal cursor-pointer">
              {opt.label}
            </Label>
            {isOther && checked && onOtherChange ? (
              <Input
                className="max-w-xs"
                value={otherValue || ""}
                onChange={(e) => onOtherChange(e.target.value)}
                placeholder="…"
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function RadioOptions({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid gap-2" role="radiogroup">
      {options.map((opt) => {
        const selected = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-2 text-left text-sm",
              selected
                ? "border-primary bg-primary/10"
                : "border-border bg-muted/20 hover:bg-muted/40"
            )}
          >
            <span
              className={cn(
                "inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                selected ? "border-primary" : "border-muted-foreground/40"
              )}
              aria-hidden
            >
              {selected ? <span className="h-2 w-2 rounded-full bg-primary" /> : null}
            </span>
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function MatrixTable({
  items,
  values,
  onChange,
  isUz,
}: {
  items: readonly { key: string; labelRu: string; labelUz: string }[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  isUz: boolean;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/40">
            <th className="text-left p-2 font-medium">{isUz ? "Ko‘rsatkich" : "Показатель"}</th>
            {[1, 2, 3, 4, 5].map((n) => (
              <th key={n} className="p-2 w-12 text-center font-medium">
                {n}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.key} className="border-t border-border">
              <td className="p-2 align-middle">{isUz ? item.labelUz : item.labelRu}</td>
              {[1, 2, 3, 4, 5].map((n) => {
                const selected = values[item.key] === String(n);
                return (
                  <td key={n} className="p-1 text-center">
                    <button
                      type="button"
                      onClick={() => onChange(item.key, String(n))}
                      className={cn(
                        "inline-flex h-8 w-8 items-center justify-center rounded-md border text-sm",
                        selected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-transparent hover:border-border hover:bg-muted/50"
                      )}
                      aria-label={`${item.key}-${n}`}
                      aria-pressed={selected}
                    >
                      {n}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function FeedbackSurvey() {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const isUz = language === "uz";
  const [form, setForm] = useState<AnswersState>(INITIAL);
  const [submitting, setSubmitting] = useState(false);

  const labels = useMemo(
    () => ({
      analyticsTools: [
        { value: "excel", label: "Excel / Google Sheets" },
        { value: "cabinet", label: isUz ? "Marketpleys kabineti hisobotlari" : "отчёты кабинета маркетплейса" },
        { value: "other", label: isUz ? "boshqa xizmat" : "другой сервис" },
        { value: "none", label: isUz ? "tizimli hech narsa yo‘q" : "ничего системного" },
      ],
      sectionsUsed: [
        { value: "summary", label: isUz ? "Yig‘indi" : "Сводка" },
        { value: "daily", label: isUz ? "Kunlik dinamika" : "Дневная динамика" },
        { value: "products", label: isUz ? "Tovarlar" : "Товары" },
        { value: "expenses", label: isUz ? "Xarajatlar" : "Расходы" },
        { value: "shipment", label: isUz ? "Yetkazib berish / jo‘natmalar" : "Поставки / отгрузки" },
        { value: "monthly", label: isUz ? "Oylik yig‘indi" : "Месячная сводка" },
        { value: "other", label: isUz ? "boshqa" : "другое" },
      ],
      sectionsNeeded: [
        { value: "summary", label: isUz ? "Yig‘indi / dashboard" : "Сводка / дашборд" },
        { value: "daily", label: isUz ? "Kunlik dinamika" : "Дневная динамика" },
        { value: "products", label: isUz ? "Tovarlar analitikasi" : "Аналитика по товарам" },
        { value: "expenses", label: isUz ? "Xarajatlar" : "Расходы" },
        { value: "shipment", label: isUz ? "Yetkazib berish / jo‘natmalar" : "Поставки / отгрузки" },
        { value: "monthly", label: isUz ? "Oylik yig‘indi" : "Месячная сводка" },
        { value: "training", label: isUz ? "O‘qitish / yordam" : "Обучение / помощь" },
        { value: "other", label: isUz ? "boshqa" : "другое" },
      ],
      outcomes: [
        { value: "faster", label: isUz ? "Asosiy raqamlarni tezroq ko‘raman" : "быстрее вижу ключевые цифры" },
        { value: "profit", label: isUz ? "Foydani yaxshiroq tushunaman" : "лучше понимаю прибыль" },
        { value: "unprofitable", label: isUz ? "Zararli tovarlarni osonroq topaman" : "проще находить убыточные товары" },
        { value: "lessExcel", label: isUz ? "Excel / qo‘lda hisobotlarga kamroq vaqt" : "меньше времени на Excel / ручные отчёты" },
        { value: "expenses", label: isUz ? "Xarajatlarni qulayroq nazorat qilaman" : "удобнее контролировать расходы" },
        { value: "shipment", label: isUz ? "Yetkazib berish bo‘yicha qarorlar osonroq" : "проще принимать решения по поставкам" },
        { value: "none", label: isUz ? "Hali sezilarli o‘zgarish yo‘q" : "пока заметных изменений нет" },
        { value: "other", label: isUz ? "boshqa" : "другое" },
      ],
      difficulties: [
        { value: "metrics", label: isUz ? "Metrikalarni o‘qish / hisoblash tushunarsiz" : "непонятно, как считать / читать метрики" },
        { value: "upload", label: isUz ? "Hisobot yuklash noqulay" : "неудобная загрузка отчётов" },
        { value: "mismatch", label: isUz ? "Ma’lumotlar kabinet bilan mos kelmaydi" : "данные расходятся с кабинетом маркетплейса" },
        { value: "slow", label: isUz ? "Sekin ishlaydi" : "медленно работает" },
        { value: "filters", label: isUz ? "Kerakli hisobot / filtrlar yetishmaydi" : "не хватает нужных отчётов / фильтров" },
        { value: "hard", label: isUz ? "Yordamsiz tushunish qiyin" : "сложно разобраться без помощи" },
        { value: "other", label: isUz ? "boshqa" : "другое" },
        { value: "none", label: isUz ? "Maxsus muammo bo‘lmadi" : "особых проблем не было" },
      ],
    }),
    [isUz]
  );

  const setField = <K extends keyof AnswersState>(key: K, value: AnswersState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.tenure && !form.nps && !form.comment.trim()) {
      toast.error(t("survey.fillRequired"));
      return;
    }
    setSubmitting(true);
    try {
      const nps = form.nps ? Number(form.nps) : null;
      const helpfulness = form.helpfulness ? Number(form.helpfulness) : null;
      await apiPost<{ id: string }>("/api/feedback/surveys", {
        answers: form,
        nps,
        helpfulness,
        client_name: null,
        client_contact: form.clientContact.trim() || null,
      });
      toast.success(t("survey.sent"), { description: t("survey.sentDesc") });
      setForm(INITIAL);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(msg || t("survey.error"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <MainLayout>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ClipboardList className="h-7 w-7 text-primary shrink-0" />
            {t("survey.title")}
          </h1>
          <p className="text-muted-foreground mt-1 max-w-3xl">{t("survey.subtitle")}</p>
        </div>
        <Button type="button" variant="outline" onClick={() => navigate(-1)} className="shrink-0 gap-2">
          <ArrowLeft className="h-4 w-4" />
          {t("survey.back")}
        </Button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 pb-10">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section1")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>{t("survey.q1")}</Label>
              <RadioOptions
                value={form.tenure}
                onChange={(v) => setField("tenure", v)}
                options={[
                  { value: "lt1m", label: t("survey.tenure.lt1m") },
                  { value: "1to3m", label: t("survey.tenure.1to3m") },
                  { value: "3to6m", label: t("survey.tenure.3to6m") },
                  { value: "gt6m", label: t("survey.tenure.gt6m") },
                ]}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q2")}</Label>
              <RadioOptions
                value={form.frequency}
                onChange={(v) => setField("frequency", v)}
                options={[
                  { value: "daily", label: t("survey.freq.daily") },
                  { value: "fewWeek", label: t("survey.freq.fewWeek") },
                  { value: "weekly", label: t("survey.freq.weekly") },
                  { value: "rare", label: t("survey.freq.rare") },
                ]}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q3")}</Label>
              <ScaleRow value={form.helpfulness} onChange={(v) => setField("helpfulness", v)} min={1} max={10} />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q4")}</Label>
              <ScaleRow value={form.nps} onChange={(v) => setField("nps", v)} min={0} max={10} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section2")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label>{t("survey.q5")}</Label>
            <OptionList
              idPrefix="analytics-tools"
              options={labels.analyticsTools}
              value={form.analyticsTools}
              onChange={(v) => setField("analyticsTools", v)}
              otherKey="other"
              otherValue={form.analyticsOther}
              onOtherChange={(v) => setField("analyticsOther", v)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section3")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">{t("survey.importanceHint")}</p>
            <MatrixTable
              items={IMPORTANCE_KEYS}
              values={form.importance}
              onChange={(key, value) =>
                setForm((prev) => ({ ...prev, importance: { ...prev.importance, [key]: value } }))
              }
              isUz={isUz}
            />
            <div className="space-y-2">
              <Label htmlFor="otherMetrics">{t("survey.q16")}</Label>
              <Input id="otherMetrics" value={form.otherMetrics} onChange={(e) => setField("otherMetrics", e.target.value)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section4")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>{t("survey.q17")}</Label>
              <OptionList
                idPrefix="sections-used"
                options={labels.sectionsUsed}
                value={form.sectionsUsed}
                onChange={(v) => setField("sectionsUsed", v)}
                otherKey="other"
                otherValue={form.sectionsUsedOther}
                onOtherChange={(v) => setField("sectionsUsedOther", v)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mostUseful">{t("survey.q18")}</Label>
              <Input id="mostUseful" value={form.mostUseful} onChange={(e) => setField("mostUseful", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="leastUsed">{t("survey.q19")}</Label>
              <Textarea id="leastUsed" value={form.leastUsed} onChange={(e) => setField("leastUsed", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q20")}</Label>
              <OptionList
                idPrefix="sections-needed"
                options={labels.sectionsNeeded}
                value={form.sectionsNeeded}
                onChange={(v) => setField("sectionsNeeded", v)}
                otherKey="other"
                otherValue={form.sectionsNeededOther}
                onOtherChange={(v) => setField("sectionsNeededOther", v)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section5")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">{t("survey.ratingHint")}</p>
            <MatrixTable
              items={RATING_KEYS}
              values={form.ratings}
              onChange={(key, value) =>
                setForm((prev) => ({ ...prev, ratings: { ...prev.ratings, [key]: value } }))
              }
              isUz={isUz}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section6")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label>{t("survey.q28")}</Label>
            <RadioOptions
              value={form.onboardingHelp}
              onChange={(v) => setField("onboardingHelp", v)}
              options={[
                { value: "yes", label: t("survey.onboarding.yes") },
                { value: "partial", label: t("survey.onboarding.partial") },
                { value: "no", label: t("survey.onboarding.no") },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section7")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>{t("survey.q29")}</Label>
              <OptionList
                idPrefix="outcomes"
                options={labels.outcomes}
                value={form.outcomes}
                onChange={(v) => setField("outcomes", v)}
                otherKey="other"
                otherValue={form.outcomesOther}
                onOtherChange={(v) => setField("outcomesOther", v)}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q30")}</Label>
              <RadioOptions
                value={form.timeSaved}
                onChange={(v) => setField("timeSaved", v)}
                options={[
                  { value: "none", label: t("survey.time.none") },
                  { value: "lt1", label: t("survey.time.lt1") },
                  { value: "1to3", label: t("survey.time.1to3") },
                  { value: "3to5", label: t("survey.time.3to5") },
                  { value: "gt5", label: t("survey.time.gt5") },
                ]}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section8")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>{t("survey.q31")}</Label>
              <OptionList
                idPrefix="difficulties"
                options={labels.difficulties}
                value={form.difficulties}
                onChange={(v) => setField("difficulties", v)}
                otherKey="other"
                otherValue={form.difficultiesOther}
                onOtherChange={(v) => setField("difficultiesOther", v)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="annoying">{t("survey.q32")}</Label>
              <Textarea id="annoying" value={form.annoying} onChange={(e) => setField("annoying", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="missing">{t("survey.q33")}</Label>
              <Textarea id="missing" value={form.missing} onChange={(e) => setField("missing", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="oneChange">{t("survey.q34")}</Label>
              <Textarea id="oneChange" value={form.oneChange} onChange={(e) => setField("oneChange", e.target.value)} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("survey.section9")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>{t("survey.q35")}</Label>
              <ScaleRow value={form.supportRating} onChange={(v) => setField("supportRating", v)} min={1} max={5} />
            </div>
            <div className="space-y-2">
              <Label>{t("survey.q36")}</Label>
              <RadioOptions
                value={form.continueUsing}
                onChange={(v) => setField("continueUsing", v)}
                options={[
                  { value: "yes", label: t("survey.continue.yes") },
                  { value: "likelyYes", label: t("survey.continue.likelyYes") },
                  { value: "unsure", label: t("survey.continue.unsure") },
                  { value: "likelyNo", label: t("survey.continue.likelyNo") },
                  { value: "no", label: t("survey.continue.no") },
                ]}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="improveToStay">{t("survey.q37")}</Label>
              <Textarea id="improveToStay" value={form.improveToStay} onChange={(e) => setField("improveToStay", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="comment">{t("survey.q38")}</Label>
              <Textarea id="comment" value={form.comment} onChange={(e) => setField("comment", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="clientContact">{t("survey.clientContact")}</Label>
              <Input
                id="clientContact"
                value={form.clientContact}
                onChange={(e) => setField("clientContact", e.target.value)}
                placeholder={t("survey.clientContactPlaceholder")}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-wrap gap-3 sticky bottom-2 bg-background/95 backdrop-blur border border-border rounded-lg p-3 shadow-sm">
          <Button type="submit" disabled={submitting} className="min-w-40">
            {submitting ? t("survey.sending") : t("survey.submit")}
          </Button>
        </div>
      </form>
    </MainLayout>
  );
}
