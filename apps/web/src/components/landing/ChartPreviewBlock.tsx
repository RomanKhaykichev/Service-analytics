import { Container } from "./Container";

/**
 * Блок-превью графика/аналитики между Hero и «Возможности».
 * Оформление как у картинки под «Мы подготовили десятки удобных отчетов…».
 */
export function ChartPreviewBlock() {
  return (
    <section className="pt-8 sm:pt-10 md:pt-12 pb-1 sm:pb-2 md:pb-3 bg-white">
      <Container>
        <div className="flex justify-center max-w-5xl w-full mx-auto overflow-hidden rounded-2xl border-2 border-[#7F7F7F]">
          <img
            src="/analytics-chart.png"
            alt="График заказов и продаж, данные по дням"
            className="w-full rounded-2xl"
          />
        </div>
      </Container>
    </section>
  );
}
