import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/LanguageContext";

interface SummaryTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabsData = [
  { id: "summary", labelKey: "tabs.summary" },
  { id: "daily", labelKey: "tabs.daily" },
  { id: "products", labelKey: "tabs.products" },
  { id: "expenses", labelKey: "tabs.expensesExtra" },
  { id: "shipment", labelKey: "tabs.shipment" },
  { id: "monthly", labelKey: "tabs.monthly" },
  { id: "expenses-analytics", labelKey: "tabs.services" },
];

export function SummaryTabs({ activeTab, onTabChange }: SummaryTabsProps) {
  const { t } = useLanguage();
  
  const getTabLabel = (id: string) => {
    switch (id) {
      case "summary": return t('tabs.summary');
      case "daily": return t('tabs.daily');
      case "products": return t('tabs.products');
      case "expenses-analytics": return t('tabs.services');
      case "expenses": return t('tabs.expensesExtra');
      case "shipment": return t('tabs.shipmentLabel');
      case "monthly": return t('tabs.monthly');
      default: return id;
    }
  };
  
  return (
    <div className="flex items-center gap-1 border-b border-border">
      {tabsData.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            "px-4 py-3 text-sm font-medium transition-all duration-200 border-b-2 -mb-px",
            activeTab === tab.id
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
          )}
        >
          {getTabLabel(tab.id)}
        </button>
      ))}
    </div>
  );
}
