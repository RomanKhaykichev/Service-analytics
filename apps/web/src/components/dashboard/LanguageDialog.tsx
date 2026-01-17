import { Globe, Check } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useLanguage, Language } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";

interface LanguageDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const languages: { code: Language; name: string; nativeName: string; flag: string }[] = [
  { code: 'ru', name: 'Русский', nativeName: 'Русский', flag: '🇷🇺' },
  { code: 'uz', name: 'Узбекский', nativeName: "O'zbekcha", flag: '🇺🇿' },
];

export function LanguageDialog({ open, onOpenChange }: LanguageDialogProps) {
  const { language, setLanguage, t } = useLanguage();

  const handleSelectLanguage = (lang: Language) => {
    setLanguage(lang);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            {t('language.title')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-2 pt-2">
          {languages.map((lang) => (
            <Button
              key={lang.code}
              variant="ghost"
              className={cn(
                "w-full justify-start gap-3 h-14 text-left",
                language === lang.code && "bg-primary/10 border border-primary/20"
              )}
              onClick={() => handleSelectLanguage(lang.code)}
            >
              <span className="text-2xl">{lang.flag}</span>
              <div className="flex flex-col items-start">
                <span className="font-medium">{lang.nativeName}</span>
                <span className="text-xs text-muted-foreground">{lang.name}</span>
              </div>
              {language === lang.code && (
                <Check className="w-5 h-5 ml-auto text-primary" />
              )}
            </Button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
