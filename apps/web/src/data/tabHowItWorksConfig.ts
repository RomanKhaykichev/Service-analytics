import type { DashboardTabId } from "@/data/trainingVideos";

export interface TabHowItWorksItem {
  textKey: string;
  italic?: boolean;
}

export interface TabHowItWorksTabConfig {
  items: TabHowItWorksItem[];
  videoId: string;
}

export const TAB_HOW_IT_WORKS_CONFIG: Record<DashboardTabId, TabHowItWorksTabConfig> = {
  summary: {
    videoId: "1",
    items: [
      { textKey: "howItWorks.summary.item1" },
      { textKey: "howItWorks.summary.item2" },
      { textKey: "howItWorks.summary.item4" },
      { textKey: "howItWorks.summary.item3" },
    ],
  },
  daily: {
    videoId: "2",
    items: [
      { textKey: "howItWorks.daily.item1" },
      { textKey: "howItWorks.daily.item2" },
      { textKey: "howItWorks.daily.item3" },
    ],
  },
  products: {
    videoId: "3",
    items: [
      { textKey: "howItWorks.products.item1" },
      { textKey: "howItWorks.products.item2" },
      { textKey: "howItWorks.products.item3" },
      { textKey: "howItWorks.products.item4" },
    ],
  },
  expenses: {
    videoId: "4",
    items: [
      { textKey: "expense.howItWorks1" },
      { textKey: "expense.howItWorks2" },
      { textKey: "expense.howItWorks3" },
      { textKey: "expense.howItWorks4", italic: true },
    ],
  },
  shipment: {
    videoId: "5",
    items: [
      { textKey: "howItWorks.shipment.item1" },
      { textKey: "howItWorks.shipment.item2" },
      { textKey: "howItWorks.shipment.item3" },
    ],
  },
  monthly: {
    videoId: "6",
    items: [
      { textKey: "howItWorks.monthly.item1" },
      { textKey: "howItWorks.monthly.item2" },
      { textKey: "howItWorks.monthly.item3" },
    ],
  },
};
