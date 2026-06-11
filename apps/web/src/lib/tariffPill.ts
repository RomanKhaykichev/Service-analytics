/** Стили бейджей тарифов — как в ProfileDialog и Admin. */
export function getMonthTariffPillClass(planId: "month5" | "month10"): string {
  if (planId === "month5") {
    return "bg-gradient-to-r from-indigo-300 to-violet-100 text-indigo-900";
  }
  return "bg-blue-400 text-white shadow-md shadow-blue-600/30";
}
