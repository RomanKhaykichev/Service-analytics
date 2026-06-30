export interface TrainingVideoItem {
  id: string;
  src: string;
  titleKey: string;
  descriptionKey: string;
}

export type DashboardTabId =
  | "summary"
  | "daily"
  | "products"
  | "expenses"
  | "shipment"
  | "monthly";

export const TRAINING_VIDEO_PLAYLIST: TrainingVideoItem[] = [
  {
    id: "1",
    src: "/videos/01-summary-tab.mp4",
    titleKey: "learning.videoSummary.title",
    descriptionKey: "learning.videoSummary.desc",
  },
  {
    id: "2",
    src: "/videos/02-by-day.mp4",
    titleKey: "learning.videoByDay.title",
    descriptionKey: "learning.videoByDay.desc",
  },
  {
    id: "3",
    src: "/videos/03-goods.mp4",
    titleKey: "learning.videoGoods.title",
    descriptionKey: "learning.videoGoods.desc",
  },
  {
    id: "4",
    src: "/videos/04-additional-expenses.mp4",
    titleKey: "learning.videoAdditionalExpenses.title",
    descriptionKey: "learning.videoAdditionalExpenses.desc",
  },
  {
    id: "5",
    src: "/videos/05-shipment.mp4",
    titleKey: "learning.videoShipment.title",
    descriptionKey: "learning.videoShipment.desc",
  },
  {
    id: "6",
    src: "/videos/06-monthly.mp4",
    titleKey: "learning.videoMonthly.title",
    descriptionKey: "learning.videoMonthly.desc",
  },
];

export function getTrainingVideoById(id: string): TrainingVideoItem | undefined {
  return TRAINING_VIDEO_PLAYLIST.find((v) => v.id === id);
}

export function getTrainingVideoForTab(tab: DashboardTabId): TrainingVideoItem | undefined {
  const tabToVideoId: Record<DashboardTabId, string> = {
    summary: "1",
    daily: "2",
    products: "3",
    expenses: "4",
    shipment: "5",
    monthly: "6",
  };
  return getTrainingVideoById(tabToVideoId[tab]);
}
