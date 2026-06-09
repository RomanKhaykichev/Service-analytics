import { forwardRef, useImperativeHandle, useState } from "react";
import { createPortal } from "react-dom";
import { Info, X, ShieldCheck, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useLanguage } from "@/contexts/LanguageContext";
import { UZUM_API_KEYS_URL } from "@/lib/uzumApiStorage";
import { UzumApiKeyConnectForm } from "@/components/dashboard/UzumApiKeyConnectForm";
import { Link } from "react-router-dom";
export interface HelpConnectApiDialogHandle {
  open: () => void;
}

interface HelpConnectApiDialogProps {
  disabled?: boolean;
}

const stepInstructionClassName =
  "px-3 py-2 text-xs font-semibold leading-relaxed text-slate-800 dark:text-foreground/95 sm:text-[13px]";

function StepZoomImage({
  src,
  ariaLabel,
  onTogglePreview,
}: {
  src: string;
  ariaLabel: string;
  onTogglePreview: (src: string) => void;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      onClick={() => onTogglePreview(src)}
      className="group flex min-h-0 w-full cursor-zoom-in items-center justify-center overflow-hidden rounded-lg border border-slate-200/90 bg-white text-left shadow-sm outline-none ring-offset-background transition hover:border-primary/40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-primary/30 dark:border-zinc-700 dark:bg-zinc-950/80 dark:hover:bg-zinc-900"
    >
      <img
        src={src}
        alt=""
        className="max-h-[200px] w-full object-contain object-top sm:max-h-[220px] pointer-events-none"
      />
    </button>
  );
}

const HELP_CONNECT_API_STEP1_IMAGE_URLS = [
  "/images/help-connect-api-uzum-profile-menu.png",
  "/images/help-connect-api-uzum-api-keys.png",
  "/images/help-connect-api-uzum-create-key.png",
] as const;

export const HelpConnectApiDialog = forwardRef<HelpConnectApiDialogHandle, HelpConnectApiDialogProps>(
  function HelpConnectApiDialog({ disabled }, ref) {
    const { t } = useLanguage();
    const [open, setOpen] = useState(false);
    const [stepImagePreview, setStepImagePreview] = useState<string | null>(null);

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
      if (!value) {
        setStepImagePreview(null);
      }
    };

    return (
      <>
        <Dialog open={open} onOpenChange={handleOpenChange}>
          <DialogContent className="max-w-[54rem] w-[calc(100vw-1.5rem)] max-h-[92vh] flex flex-col gap-0 border-slate-200/90 bg-white p-4 shadow-xl dark:border-zinc-700 dark:bg-zinc-950 sm:p-6 sm:max-w-[54rem]">
            <DialogHeader className="flex-shrink-0 space-y-0 border-b border-slate-200/80 pb-4 dark:border-zinc-700/80 pr-8 sm:pr-10">
              <div className="min-w-0 space-y-2 text-left">
                <DialogTitle className="text-balance text-left text-xl font-bold leading-tight tracking-tight text-slate-900 dark:text-foreground sm:text-2xl">
                  {t("helpConnectApi.heroTitle")}
                </DialogTitle>
              </div>
            </DialogHeader>

            <div className="flex-1 overflow-y-auto pr-1 -mr-1 min-h-0 sm:pr-2 sm:-mr-2">
              <div className="mt-4 space-y-6">
                <div className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-sm dark:border-zinc-700/90 dark:bg-zinc-950/60">
                    <div className="flex min-h-0 min-w-0 flex-1 flex-col content-start">
                      <div className="flex shrink-0 items-center gap-2.5 border-b border-slate-200/90 bg-violet-50/90 px-3 py-2.5 dark:border-zinc-700/80 dark:bg-violet-950/25">
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
                          <KeyRound className="h-4 w-4" strokeWidth={2.25} aria-hidden />
                        </span>
                        <span className="text-left text-sm font-bold leading-tight text-slate-900 dark:text-foreground">
                          {t("helpConnectApi.step1Title")}
                        </span>
                      </div>
                      <div className="flex flex-col gap-2 bg-slate-50/90 p-2.5 dark:bg-zinc-900/50">
                        <p className={stepInstructionClassName}>
                          1. {t("services.instructionStep1Prefix")}
                          <a
                            href={UZUM_API_KEYS_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline font-medium"
                          >
                            {t("services.instructionStep1Link")}
                          </a>
                          {t("services.instructionStep1Suffix")}
                        </p>
                        <StepZoomImage
                          src={HELP_CONNECT_API_STEP1_IMAGE_URLS[0]}
                          ariaLabel={t("report.stepImageZoomAria")}
                          onTogglePreview={(src) =>
                            setStepImagePreview((prev) => (prev === src ? null : src))
                          }
                        />
                        <p className={stepInstructionClassName}>{t("helpConnectApi.step1Line2")}</p>
                        <StepZoomImage
                          src={HELP_CONNECT_API_STEP1_IMAGE_URLS[1]}
                          ariaLabel={t("report.stepImageZoomAria")}
                          onTogglePreview={(src) =>
                            setStepImagePreview((prev) => (prev === src ? null : src))
                          }
                        />
                        <StepZoomImage
                          src={HELP_CONNECT_API_STEP1_IMAGE_URLS[2]}
                          ariaLabel={t("report.stepImageZoomAria")}
                          onTogglePreview={(src) =>
                            setStepImagePreview((prev) => (prev === src ? null : src))
                          }
                        />
                        <p className={stepInstructionClassName}>{t("helpConnectApi.step1Line3")}</p>
                        <UzumApiKeyConnectForm
                          inputId="help-connect-api-key"
                          active={open}
                          disabled={disabled}
                          showLabel={false}
                          className="px-3 pb-1"
                          buttonClassName="w-full"
                          onSuccess={() => setOpen(false)}
                        />
                        <div className="space-y-3 px-3 pb-2">
                          <p className="text-xs font-medium leading-relaxed text-slate-600 dark:text-muted-foreground sm:text-[13px]">
                            {t("helpConnectApi.whileConnectingText")}
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-9 w-full border-2 border-primary text-sm font-bold text-primary shadow-sm hover:bg-primary/10"
                            asChild
                          >
                            <Link to="/training" onClick={() => setOpen(false)}>
                              {t("helpConnectApi.dashboardOverviewButton")}
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </div>

                    <div
                      role="note"
                      className="flex items-start gap-2.5 border-t border-slate-200/90 bg-violet-50/90 px-3 py-2.5 dark:border-zinc-700/80 dark:bg-violet-950/20"
                    >
                      <Info
                        className="mt-0.5 h-4 w-4 shrink-0 text-slate-500 dark:text-slate-400"
                        strokeWidth={2.25}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 text-xs font-medium leading-snug text-slate-700 dark:text-slate-300 sm:text-[13px]">
                        {t("helpConnectApi.step1Footnote")}
                      </span>
                    </div>
                  </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
                  <div className="flex h-full items-center justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/95 p-3 shadow-sm dark:border-emerald-800/50 dark:bg-emerald-950/35">
                    <div className="flex max-w-full flex-row items-center gap-3">
                      <a
                        href="https://t.me/PROFiboard"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 rounded-lg border border-white/80 bg-white p-0.5 shadow-md ring-1 ring-slate-200/80 transition-opacity hover:opacity-95 dark:border-zinc-700 dark:bg-zinc-950 dark:ring-zinc-700"
                      >
                        <img
                          src="/images/telegram-first-upload-qr.png"
                          alt={t("support.telegramQrAlt")}
                          className="h-[100px] w-[100px] object-contain"
                          width={100}
                          height={100}
                          loading="lazy"
                        />
                      </a>
                      <div className="flex min-w-0 flex-col gap-1.5">
                        <p className="text-left text-xs font-bold leading-tight text-emerald-950 dark:text-emerald-50 sm:text-[13px] sm:leading-snug">
                          {t("helpConnectApi.telegramHelpTitle")}
                        </p>
                        <p className="text-left text-xs font-normal leading-snug text-slate-700 dark:text-emerald-100/90 sm:text-[13px] sm:leading-relaxed">
                          {t("helpConnectApi.telegramHelpBody")}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex h-full flex-col justify-center rounded-xl border border-emerald-200/90 bg-emerald-50/95 p-3 text-left shadow-sm dark:border-emerald-800/50 dark:bg-emerald-950/35">
                    <div className="grid grid-cols-[auto_1fr] gap-x-2.5 gap-y-1.5">
                      <ShieldCheck
                        className="row-start-1 h-7 w-7 shrink-0 self-start text-emerald-700 dark:text-emerald-300"
                        strokeWidth={2.25}
                        aria-hidden
                      />
                      <span className="row-start-1 min-w-0 self-start pt-0.5 text-xs font-bold leading-snug text-emerald-950 dark:text-emerald-50 sm:text-[13px]">
                        {t("helpConnectApi.dataSafetyTitle")}
                      </span>
                      <span className="col-span-2 row-start-2 w-full text-xs font-normal leading-relaxed text-slate-600 dark:text-muted-foreground sm:text-[13px]">
                        {t("helpConnectApi.dataSafetyBody")}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-5 flex flex-shrink-0 items-center justify-end gap-3 border-t border-slate-200/90 pt-4 dark:border-zinc-700/80">
              <Button
                variant="outline"
                onClick={() => setOpen(false)}
                className="h-10 min-w-[104px] border-2 border-slate-300 bg-white font-bold text-slate-800 shadow-sm hover:bg-slate-50 dark:border-zinc-600 dark:bg-zinc-950 dark:text-foreground dark:hover:bg-zinc-900"
              >
                {t("report.close")}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {stepImagePreview && typeof document !== "undefined"
          ? createPortal(
              <div
                className="fixed inset-0 z-[9999] flex cursor-zoom-out items-center justify-center bg-black/88 p-4 sm:p-10"
                role="dialog"
                aria-modal="true"
                aria-label={t("report.stepImageZoomAria")}
                onClick={() => setStepImagePreview(null)}
              >
                <button
                  type="button"
                  className="absolute right-3 top-3 z-[10000] cursor-pointer rounded-md bg-background/95 p-2 text-foreground shadow-md ring-1 ring-border hover:bg-muted"
                  onClick={(e) => {
                    e.stopPropagation();
                    setStepImagePreview(null);
                  }}
                  aria-label={t("report.close")}
                >
                  <X className="h-5 w-5" />
                </button>
                <img
                  src={stepImagePreview}
                  alt=""
                  className="max-h-[min(90vh,calc(100dvh-4rem))] max-w-[min(100%,calc(100vw-2rem))] w-auto object-contain"
                  onClick={(e) => {
                    e.stopPropagation();
                    setStepImagePreview(null);
                  }}
                />
              </div>,
              document.body,
            )
          : null}
      </>
    );
  },
);
