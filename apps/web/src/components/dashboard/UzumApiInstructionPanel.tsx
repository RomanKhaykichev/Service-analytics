import { Info } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { UZUM_API_KEYS_URL } from "@/lib/uzumApiStorage";

export function UzumApiInstructionPanel() {
  const { t } = useLanguage();

  return (
    <div className="bg-primary/10 border border-primary/20 rounded-lg p-2.5">
      <div className="flex items-start gap-2">
        <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" aria-hidden />
        <div className="text-xs text-foreground min-w-0">
          <p className="font-semibold mb-1.5 text-sm">{t("services.instructionTitle")}</p>
          <ul className="text-muted-foreground leading-snug space-y-1 list-disc list-inside">
            <li>
              {t("services.instructionStep1Prefix")}
              <a
                href={UZUM_API_KEYS_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                {t("services.instructionStep1Link")}
              </a>
              {t("services.instructionStep1Suffix")}
            </li>
            <li>{t("services.instructionStep2")}</li>
            <li>{t("services.instructionStep3")}</li>
            <li className="text-warning font-medium">{t("services.instructionImportant")}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
