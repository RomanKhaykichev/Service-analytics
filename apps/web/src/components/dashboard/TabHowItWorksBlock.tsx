import { useState } from "react";
import { Link } from "react-router-dom";
import { CircleHelp, ChevronDown, PlayCircle, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useLanguage } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import { TAB_HOW_IT_WORKS_CONFIG } from "@/data/tabHowItWorksConfig";
import {
  getTrainingVideoById,
  type DashboardTabId,
} from "@/data/trainingVideos";

const TAB_LABEL_KEYS: Record<DashboardTabId, string> = {
  summary: "tabs.summary",
  daily: "tabs.daily",
  products: "tabs.products",
  cogs: "tabs.cogs",
  "expenses-analytics": "tabs.services",
  expenses: "tabs.expensesExtra",
  shipment: "tabs.shipmentLabel",
  monthly: "tabs.monthly",
};

function getTabLabel(t: (key: string) => string, tab: DashboardTabId): string {
  return t(TAB_LABEL_KEYS[tab]);
}

function fillTemplate(template: string, vars: Record<string, string>): string {
  return Object.entries(vars).reduce(
    (s, [k, v]) => s.replaceAll(`{${k}}`, v),
    template
  );
}

interface TabHowItWorksTriggerProps {
  expanded: boolean;
  onExpandedChange: (expanded: boolean) => void;
  className?: string;
}

/** Компактная кнопка в строке вкладок */
export function TabHowItWorksTrigger({
  expanded,
  onExpandedChange,
  className,
}: TabHowItWorksTriggerProps) {
  const { t } = useLanguage();

  const collapseLabel = expanded
    ? t("summary.weeklyInsights.collapse")
    : t("howItWorks.triggerAria");

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Card
          className={cn(
            "bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 shrink-0 w-fit max-w-full cursor-pointer transition-colors hover:bg-blue-100/70 dark:hover:bg-blue-900/40",
            className
          )}
        >
          <CardContent className="py-2 px-2">
            <button
              type="button"
              onClick={() => onExpandedChange(!expanded)}
              className="flex items-center gap-1 text-left"
              aria-expanded={expanded}
              aria-label={collapseLabel}
            >
              <div className="rounded-full bg-blue-100 dark:bg-blue-900 shrink-0 p-0.5">
                <CircleHelp className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden />
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 shrink-0 text-muted-foreground transition-transform duration-200",
                  expanded && "rotate-180"
                )}
                aria-hidden
              />
            </button>
          </CardContent>
        </Card>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs text-center">
        {t("howItWorks.triggerTooltip")}
      </TooltipContent>
    </Tooltip>
  );
}

interface TabHowItWorksPanelProps {
  tab: DashboardTabId;
  expanded: boolean;
  className?: string;
}

function HowItWorksListItemText({
  item,
  t,
}: {
  item: {
    textKey: string;
    textKeyAfter?: string;
    italic?: boolean;
    metricHelpIcon?: boolean;
    linkTo?: string;
    linkTextKey?: string;
  };
  t: (key: string) => string;
}) {
  if (item.linkTo && item.linkTextKey) {
    const before = item.textKey ? t(item.textKey) : "";
    const after = item.textKeyAfter ? t(item.textKeyAfter) : "";
    return (
      <span className={cn(item.italic && "text-muted-foreground/80 italic")}>
        {before}
        <Link
          to={item.linkTo}
          className="text-primary underline underline-offset-2 hover:text-primary/80"
        >
          {t(item.linkTextKey)}
        </Link>
        {after}
      </span>
    );
  }

  if (item.metricHelpIcon && item.textKeyAfter) {
    const before = item.textKey ? t(item.textKey) : "";
    const after = t(item.textKeyAfter);
    return (
      <span className={cn(item.italic && "text-muted-foreground/80 italic")}>
        {before ? (
          <>
            {before}{" "}
            <HelpCircle
              className="inline h-3 w-3 shrink-0 text-muted-foreground/50 align-[-2px]"
              aria-hidden
            />{" "}
            {after}
          </>
        ) : (
          <>
            <HelpCircle
              className="inline h-3 w-3 shrink-0 text-muted-foreground/50 align-[-2px]"
              aria-hidden
            />{" "}
            {after}
          </>
        )}
      </span>
    );
  }

  return (
    <span className={cn(item.italic && "text-muted-foreground/80 italic")}>
      {t(item.textKey)}
    </span>
  );
}

/** Развёрнутый блок под вкладками */
export function TabHowItWorksPanel({ tab, expanded, className }: TabHowItWorksPanelProps) {
  const { t } = useLanguage();
  const [videoOpen, setVideoOpen] = useState(false);

  const config = TAB_HOW_IT_WORKS_CONFIG[tab];
  const video = config.videoId ? getTrainingVideoById(config.videoId) : undefined;

  if (!expanded) return null;

  const tabLabel = getTabLabel(t, tab);
  const panelTitle = fillTemplate(t("howItWorks.panelTitle"), { tab: tabLabel });

  return (
    <>
      <Card
        className={cn(
          "bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800",
          className
        )}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-blue-100 dark:bg-blue-900 shrink-0 p-1 mt-0.5">
              <CircleHelp className="h-4 w-4 text-blue-600 dark:text-blue-400" aria-hidden />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-foreground">{panelTitle}</h3>
              <ul className="mt-2 text-sm text-muted-foreground space-y-1.5">
                {config.items.map((item) => (
                  <li
                    key={`${item.textKey}-${item.linkTextKey ?? ""}-${item.textKeyAfter ?? ""}`}
                    className="flex items-start gap-2"
                  >
                    <span className="text-blue-600 dark:text-blue-400">•</span>
                    <HowItWorksListItemText item={item} t={t} />
                  </li>
                ))}
              </ul>
              {video && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-3 h-8 border-blue-300/80 bg-white/60 text-blue-700 hover:bg-blue-100/80 dark:border-blue-700 dark:bg-blue-950/40 dark:text-blue-300 dark:hover:bg-blue-900/50"
                  onClick={() => setVideoOpen(true)}
                >
                  <PlayCircle className="h-4 w-4" />
                  {t("report.watchImportVideo")}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {video && (
        <Dialog open={videoOpen} onOpenChange={setVideoOpen}>
          <DialogContent className="max-w-4xl w-[calc(100vw-2rem)] gap-0 p-0 sm:max-w-4xl overflow-hidden">
            <DialogHeader className="px-4 pt-4 pb-3 text-left">
              <DialogTitle>{t(video.titleKey)}</DialogTitle>
            </DialogHeader>
            <div className="px-4 pb-4">
              <video
                key={videoOpen ? video.src : undefined}
                src={video.src}
                controls
                playsInline
                className="w-full rounded-md bg-black"
                preload="metadata"
              >
                {t("learning.videoNoHtml5")}
              </video>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
