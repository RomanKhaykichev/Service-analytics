import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/LanguageContext";

export type AdminPanelTab = "overview" | "uzum";

interface AdminPanelTabsProps {
  activeTab: AdminPanelTab;
  onTabChange: (tab: AdminPanelTab) => void;
  className?: string;
}

const tabs: { id: AdminPanelTab; labelKey: string }[] = [
  { id: "overview", labelKey: "admin.tabs.overview" },
  { id: "uzum", labelKey: "admin.tabs.uzum" },
];

export function AdminPanelTabs({ activeTab, onTabChange, className }: AdminPanelTabsProps) {
  const { t } = useLanguage();

  return (
    <div className={cn("flex items-center gap-1 border-b border-border", className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onTabChange(tab.id)}
          className={cn(
            "px-4 py-3 text-sm font-medium transition-all duration-200 border-b-2 -mb-px",
            activeTab === tab.id
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
          )}
        >
          {t(tab.labelKey)}
        </button>
      ))}
    </div>
  );
}
