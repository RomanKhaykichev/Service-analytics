export interface TrainingVideoItem {
  id: string;
  src: string;
  titleKey: string;
  descriptionKey: string;
}

export const TRAINING_VIDEO_PLAYLIST: TrainingVideoItem[] = [
  {
    id: "1",
    src: "/videos/01-import-reports.mp4",
    titleKey: "learning.videoImport.title",
    descriptionKey: "learning.videoImport.desc",
  },
  {
    id: "2",
    src: "/videos/02-summary-tab.mp4",
    titleKey: "learning.videoSummary.title",
    descriptionKey: "learning.videoSummary.desc",
  },
  {
    id: "3",
    src: "/videos/03-by-day-and-goods.mp4",
    titleKey: "learning.videoByDayAndGoods.title",
    descriptionKey: "learning.videoByDayAndGoods.desc",
  },
  {
    id: "4",
    src: "/videos/04-additional-expenses.mp4",
    titleKey: "learning.videoAdditionalExpenses.title",
    descriptionKey: "learning.videoAdditionalExpenses.desc",
  },
  {
    id: "5",
    src: "/videos/05-shipment-and-monthly.mp4",
    titleKey: "learning.videoShipmentMonthly.title",
    descriptionKey: "learning.videoShipmentMonthly.desc",
  },
];
