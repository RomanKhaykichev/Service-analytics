import analyticsChart from "@/assets/landing/analytics-chart.jpg";
import { Container } from "./Container";

/**
 * Блок-превью графика/аналитики между Hero и секцией #features.
 * Оформление как у картинки под «Мы подготовили десятки удобных отчетов…».
 */
export function ChartPreviewBlock() {
  return (
    <section className="pt-2 sm:pt-3 md:pt-4 pb-0 bg-white">
      <Container>
        <div className="flex justify-center max-w-5xl w-full mx-auto">
          <img
            src={analyticsChart}
            alt="Ноутбук с дашбордом PROFIboard: график заказов и продаж и таблица данных по дням"
            className="w-full h-auto"
          />
        </div>
      </Container>
    </section>
  );
}
