import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/MainLayout";
import { CogsView } from "@/components/dashboard/CogsView";
import { SummaryFilters } from "@/components/dashboard/SummaryFilters";
import { TabHowItWorksTrigger, TabHowItWorksPanel } from "@/components/dashboard/TabHowItWorksBlock";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";
import { useStorageShops } from "@/hooks/useStorageShops";
import { invalidateCogsDependentQueries } from "@/lib/invalidateCogsDependentQueries";
import { buildDashboardPath } from "@/lib/dashboardNav";

export default function CogsPage() {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { shops } = useStorageShops();
  const cogsDirtyRef = useRef(false);
  const [howItWorksExpanded, setHowItWorksExpanded] = useState(false);

  const [store, setStore] = useState(() => searchParams.get("shop") ?? "all");
  const selectedShop = store === "all" ? undefined : store;
  const backToDashboardPath = buildDashboardPath(searchParams);

  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (store === "all") next.delete("shop");
        else next.set("shop", store);
        return next;
      },
      { replace: true },
    );
  }, [store, setSearchParams]);

  const handleCogsDataChanged = useCallback(() => {
    cogsDirtyRef.current = true;
  }, []);

  useEffect(() => {
    return () => {
      if (cogsDirtyRef.current) {
        void invalidateCogsDependentQueries(queryClient);
        cogsDirtyRef.current = false;
      }
    };
  }, [queryClient]);

  return (
    <MainLayout>
      <div className="flex flex-col gap-6">
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {t("tabs.cogs")}
          </h1>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Button
                asChild
                size="sm"
                className="bg-primary hover:bg-primary/90 text-primary-foreground lowercase"
              >
                <Link to={backToDashboardPath}>{t("learning.back")}</Link>
              </Button>
              <TabHowItWorksTrigger
                expanded={howItWorksExpanded}
                onExpandedChange={setHowItWorksExpanded}
              />
            </div>
            <SummaryFilters
              dateFrom=""
              dateTo=""
              onDateRangeChange={() => undefined}
              store={store}
              onStoreChange={setStore}
              showStoreFilter
              showPeriodFilter={false}
              shops={shops}
            />
          </div>
        </div>

        <TabHowItWorksPanel tab="cogs" expanded={howItWorksExpanded} />

        <CogsView shop={selectedShop} onDataChanged={handleCogsDataChanged} />
      </div>
    </MainLayout>
  );
}
