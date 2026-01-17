import { Link, useLocation } from "react-router-dom";
import {
  Home,
  BarChart3,
  Package,
  TrendingUp,
  Users,
  FileText,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";

const navItemsData = [
  { icon: Home, labelKey: "nav.dashboard", path: "/" },
  { icon: BarChart3, labelKey: "nav.analytics", path: "/analytics" },
  { icon: Package, labelKey: "nav.products", path: "/products" },
  { icon: TrendingUp, labelKey: "nav.trends", path: "/trends" },
  { icon: Users, labelKey: "nav.competitors", path: "/competitors" },
  { icon: FileText, labelKey: "nav.reports", path: "/reports" },
  { icon: Settings, labelKey: "nav.dashboard", path: "/settings" },
  { icon: HelpCircle, labelKey: "nav.support", path: "/support" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const { t } = useLanguage();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex items-center justify-between h-16 px-4 border-b border-sidebar-border">
        {!collapsed && (
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center">
              <span className="text-sidebar-primary-foreground font-bold text-sm">U</span>
            </div>
            <span className="text-lg font-bold text-sidebar-foreground">UZUM Stats</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className={cn("text-sidebar-foreground hover:bg-sidebar-border hover:text-sidebar-foreground", collapsed && "mx-auto")}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </Button>
      </div>

      <nav className="p-2 space-y-1">
        {navItemsData.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-[hsl(220,14%,70%)] hover:bg-sidebar-border hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && (
                <span className="text-sm font-medium">{t(item.labelKey)}</span>
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
