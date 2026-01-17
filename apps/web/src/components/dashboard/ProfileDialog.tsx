import { useState, useEffect } from "react";
import { User, Phone, CreditCard, Calendar } from "lucide-react";
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

interface ProfileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProfileDialog({ open, onOpenChange }: ProfileDialogProps) {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);

  // Mock subscription data - in real app would come from database
  const subscriptionPlan = t('profile.tariffPlan');
  const subscriptionEndDate = "15 февраля 2025";
  const daysRemaining = 30;

  useEffect(() => {
    if (open && user) {
      loadProfile();
    }
  }, [open, user]);

  const loadProfile = async () => {
    if (!user) return;
    
    // TODO: Load profile from backend API
    // For now, load from localStorage
    const storedPhone = localStorage.getItem(`profile_phone_${user.id}`);
    if (storedPhone) {
      setPhone(storedPhone);
    }
  };

  const handleSavePhone = async () => {
    if (!user) return;
    
    setLoading(true);
    
    // TODO: Save profile to backend API
    // For now, save to localStorage
    try {
      localStorage.setItem(`profile_phone_${user.id}`, phone);
      toast.success("Телефон сохранён");
    } catch (error) {
      toast.error("Ошибка сохранения телефона");
    } finally {
      setLoading(false);
    }
  };

  const getUserName = () => {
    if (user?.user_metadata?.full_name) {
      return user.user_metadata.full_name;
    }
    return "Пользователь";
  };

  const getUserEmail = () => {
    return user?.email || "email@example.com";
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
                <Label className="text-xs text-muted-foreground">{t('profile.name')}</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                  <User className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm">{getUserName()}</span>
                </div>
              </div>

              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">{t('profile.email')}</Label>
                <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/50">
                  <span className="text-sm">{getUserEmail()}</span>
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="phone" className="text-xs text-muted-foreground">{t('profile.phone')}</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="phone"
                      placeholder="+998 90 123 45 67"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Button 
                    size="sm" 
                    onClick={handleSavePhone}
                    disabled={loading}
                  >
                    {loading ? "..." : t('profile.save')}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Subscription Section */}
          <div className="space-y-4 pt-4 border-t border-border">
            <h4 className="text-sm font-medium text-muted-foreground">{t('profile.tariffPlan')}</h4>
            
            <div className="p-4 rounded-lg bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/20">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-primary" />
                  <span className="font-medium">{subscriptionPlan}</span>
                </div>
                <Badge variant="secondary" className="bg-primary/20 text-primary">
                  {t('profile.active')}
                </Badge>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="w-4 h-4" />
                <span>{t('profile.validUntil')}: <strong className="text-foreground">{subscriptionEndDate}</strong></span>
              </div>
              
              <div className="mt-2 text-xs text-muted-foreground">
                {t('profile.daysRemaining')}: {daysRemaining}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
