import { useState, useEffect } from "react";
import { User, Phone, CreditCard, Calendar, Eye, EyeOff } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/useAuth";
import { useLanguage } from "@/contexts/LanguageContext";
import { toast } from "sonner";
import { apiGet, apiPatch } from "@/lib/api";

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const { user, refreshProfile } = useAuth();
  const { t } = useLanguage();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // Subscription data based on user trial info
  const subscriptionPlan = t('profile.tariffPlan');
  const rawDaysLeft = typeof user?.trial_days_left === "number" ? user.trial_days_left : null;
  const daysRemaining = rawDaysLeft != null ? Math.max(rawDaysLeft, 0) : null;
  const isTariffActive = rawDaysLeft != null && rawDaysLeft > 0;
  const dateIsSoon = rawDaysLeft != null && rawDaysLeft <= 3;
  const subscriptionEndDate = (() => {
    if (user?.trial_ends_at) {
      const d = new Date(user.trial_ends_at);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("ru-RU");
      }
    }
    if (rawDaysLeft != null) {
      const d = new Date();
      d.setDate(d.getDate() + rawDaysLeft);
      return d.toLocaleDateString("ru-RU");
    }
    return null;
  })();

  useEffect(() => {
    if (open && user) {
      loadProfile();
    }
  }, [open, user?.id]);

  const loadProfile = async () => {
    if (!user) return;
    setFullName(user.full_name ?? user.user_metadata?.full_name ?? "");
    setEmail(user.email ?? "");
    setPhone(user.phone ?? "");
    try {
      const data = await apiGet<{ full_name?: string | null; email?: string | null; phone?: string | null }>("/api/auth/me");
      setFullName(data.full_name ?? "");
      setEmail(data.email ?? "");
      setPhone(data.phone ?? "");
      setNewPassword("");
    } catch {
      // Keep values from context
    }
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    const pwd = newPassword.trim();
    if (pwd && pwd.length < 6) {
      toast.error(`${t("profile.newPassword")}: ${t("profile.passwordMinLength")}`);
      return;
    }
    setLoading(true);
    try {
      await apiPatch("/api/auth/me", {
        full_name: fullName.trim() || null,
        email: email.trim() || null,
        phone: phone.trim() || null,
        ...(pwd ? { new_password: pwd } : {}),
      });
      setNewPassword("");
      await refreshProfile();
      toast.success("Данные аккаунта сохранены");
    } catch (err) {
      let message = "Ошибка сохранения";
      if (err instanceof Error) {
        try {
          const parsed = JSON.parse(err.message);
          const d = parsed.detail;
          if (typeof d === "string") message = d;
          else if (Array.isArray(d) && d.length) message = d.map((x: { msg?: string }) => x?.msg).filter(Boolean).join(". ") || err.message;
          else if (d?.msg) message = d.msg;
        } catch {
          message = err.message;
        }
      }
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="w-5 h-5" />
            {t('profile.title')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* User Info Section */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-muted-foreground">{t('profile.accountData')}</h4>
            
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="profile-name" className="text-xs text-muted-foreground">{t('profile.name')}</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="profile-name"
                    type="text"
                    placeholder="Имя"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="profile-email" className="text-xs text-muted-foreground">{t('profile.email')}</Label>
                <Input
                  id="profile-email"
                  type="email"
                  placeholder="email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="profile-phone" className="text-xs text-muted-foreground">{t('profile.phone')}</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="profile-phone"
                    type="tel"
                    placeholder="+998 90 123 45 67"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="profile-password" className="text-xs text-muted-foreground">{t('profile.newPassword')}</Label>
                <div className="relative">
                  <Input
                    id="profile-password"
                    type={showPassword ? "text" : "password"}
                    placeholder={t('profile.newPasswordPlaceholder')}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="pr-10 text-sm placeholder:text-xs"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? t('profile.hidePassword') : t('profile.showPassword')}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4 text-muted-foreground" /> : <Eye className="h-4 w-4 text-muted-foreground" />}
                  </Button>
                </div>
              </div>

              <Button
                className="w-full"
                onClick={handleSaveProfile}
                disabled={loading}
              >
                {loading ? "..." : t('profile.save')}
              </Button>
            </div>
          </div>

          {/* Subscription Section */}
          <div className="space-y-4 pt-4 border-t border-border">
            <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-primary" />
                  <span className="font-medium">{subscriptionPlan}</span>
                </div>
                <Badge
                  variant="secondary"
                  className={
                    isTariffActive
                      ? "bg-green-500 text-white"
                      : "bg-red-500 text-white"
                  }
                >
                  {isTariffActive ? t('profile.active') : t('profile.inactive')}
                </Badge>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="w-4 h-4" />
                <span>
                  {t('profile.validUntil')}{": "}
                  <strong className={dateIsSoon ? "text-red-600" : "text-foreground"}>
                    {subscriptionEndDate ?? "—"}
                  </strong>
                </span>
              </div>
              
              <div className="mt-2 text-sm text-muted-foreground">
                {t('profile.daysRemaining')}{": "}
                {daysRemaining != null ? (
                  <strong className="text-foreground text-base">{daysRemaining}</strong>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
