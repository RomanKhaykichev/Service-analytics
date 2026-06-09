import { forwardRef, useImperativeHandle, useState } from "react";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useLanguage } from "@/contexts/LanguageContext";
import { UzumApiInstructionPanel } from "@/components/dashboard/UzumApiInstructionPanel";
import { UzumApiKeyConnectForm } from "@/components/dashboard/UzumApiKeyConnectForm";

export interface UzumApiConnectDialogHandle {
  open: () => void;
}

interface UzumApiConnectDialogProps {
  disabled?: boolean;
  showTrigger?: boolean;
  onOpenHelpGuide?: () => void;
}

export const UzumApiConnectDialog = forwardRef<UzumApiConnectDialogHandle, UzumApiConnectDialogProps>(
  function UzumApiConnectDialog({ disabled, showTrigger = true, onOpenHelpGuide }, ref) {
    const { t } = useLanguage();
    const [open, setOpen] = useState(false);

    useImperativeHandle(
      ref,
      () => ({
        open: () => {
          if (disabled) return;
          setOpen(true);
        },
      }),
      [disabled],
    );

    const handleOpenChange = (value: boolean) => {
      if (disabled) return;
      setOpen(value);
    };

    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        {showTrigger && (
          <DialogTrigger asChild>
            <div className="flex flex-col items-end">
              <Button
                type="button"
                className="bg-primary hover:bg-primary/90 text-primary-foreground gap-2 px-4"
                disabled={disabled}
              >
                <KeyRound className="w-4 h-4" />
                <span className="hidden sm:inline">{t("header.connectApi")}</span>
              </Button>
            </div>
          </DialogTrigger>
        )}
        <DialogContent className="max-w-lg bg-card border-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              {t("services.title")}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <UzumApiInstructionPanel
              onOpenDetailedGuide={
                onOpenHelpGuide
                  ? () => {
                      setOpen(false);
                      onOpenHelpGuide();
                    }
                  : undefined
              }
            />
            <UzumApiKeyConnectForm
              inputId="uzum-api-key-dialog"
              active={open}
              disabled={disabled}
              onSuccess={() => setOpen(false)}
            />
          </div>
        </DialogContent>
      </Dialog>
    );
  },
);
