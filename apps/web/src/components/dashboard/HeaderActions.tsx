import { useState } from "react";
import { HelpCircle, User, ChevronDown, LogOut, CreditCard, Globe, PlayCircle, MessageCircle, HelpCircle as FAQ, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ReportUploadDialog } from "./ReportUploadDialog";
import { PricingDialog } from "./PricingDialog";
import { ProfileDialog } from "./ProfileDialog";
import { LanguageDialog } from "./LanguageDialog";
import { useNavigate, Link } from "react-router-dom";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";

function getUserDisplayName(user: { full_name?: string; user_metadata?: { full_name?: string }; email?: string } | null): string {
  if (!user) return "Пользователь";
  if (user.full_name) return user.full_name;
  if (user.user_metadata?.full_name) return user.user_metadata.full_name;
  if (user.email) return user.email;
  return "Пользователь";
}

export function HeaderActions() {
  const { t } = useLanguage();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [pricingOpen, setPricingOpen] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    toast.success(t('header.loggedOut'));
    navigate('/landing?auth=open');
  };
  const [profileOpen, setProfileOpen] = useState(false);
  const [languageOpen, setLanguageOpen] = useState(false);
  const displayName = getUserDisplayName(user);

  return (
    <div className="flex items-center gap-6">
      {/* Report Upload */}
      <ReportUploadDialog />

      {/* Help */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <HelpCircle className="w-5 h-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 bg-card border-border">
          <DropdownMenuLabel>{t('header.help')}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer">
            <FAQ className="w-4 h-4 mr-2" />
            {t('header.faq')}
          </DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer">
            <PlayCircle className="w-4 h-4 mr-2" />
            {t('header.videoTutorials')}
          </DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer">
            <MessageCircle className="w-4 h-4 mr-2" />
            {t('header.support')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* User Profile */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="gap-2 px-3">
            <User className="w-5 h-5" />
            <div className="flex flex-col items-start text-left">
              <span className="text-sm font-medium">{displayName}</span>
              <span className="text-xs text-muted-foreground">до 15.02.2025</span>
            </div>
            <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 bg-card border-border">
          <DropdownMenuLabel>{t('header.myAccount')}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer" onClick={() => setProfileOpen(true)}>
            <User className="w-4 h-4 mr-2" />
            {t('header.profile')}
          </DropdownMenuItem>
          {user?.is_admin && (
            <DropdownMenuItem className="cursor-pointer" asChild>
              <Link to="/admin">
                <ShieldCheck className="w-4 h-4 mr-2" />
                {t('header.adminPanel')}
              </Link>
            </DropdownMenuItem>
          )}
          <DropdownMenuItem className="cursor-pointer" onClick={() => setPricingOpen(true)}>
            <CreditCard className="w-4 h-4 mr-2" />
            {t('header.tariff')}
          </DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer text-primary" onClick={() => setPricingOpen(true)}>
            <CreditCard className="w-4 h-4 mr-2" />
            {t('header.extendTariff')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer" onClick={() => setLanguageOpen(true)}>
            <Globe className="w-4 h-4 mr-2" />
            {t('header.language')}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="cursor-pointer text-destructive" onClick={handleSignOut}>
            <LogOut className="w-4 h-4 mr-2" />
            {t('header.logout')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Pricing Dialog */}
      <PricingDialog open={pricingOpen} onOpenChange={setPricingOpen} />

      {/* Profile Dialog */}
      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />

      {/* Language Dialog */}
      <LanguageDialog open={languageOpen} onOpenChange={setLanguageOpen} />
    </div>
  );
}
