import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { useLanguage } from "@/contexts/LanguageContext";
import { TRAINING_VIDEO_PLAYLIST } from "@/data/trainingVideos";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PlayCircle, AlertCircle, ArrowLeft } from "lucide-react";

export default function Training() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [activeIndex, setActiveIndex] = useState(0);
  const [videoError, setVideoError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const playWhenLoadedRef = useRef(false);

  const active = TRAINING_VIDEO_PLAYLIST[activeIndex] ?? TRAINING_VIDEO_PLAYLIST[0];

  const handleSelect = useCallback((index: number) => {
    setActiveIndex(index);
    setVideoError(false);
    if (index === activeIndex) {
      queueMicrotask(() => void videoRef.current?.play().catch(() => {}));
    } else {
      playWhenLoadedRef.current = true;
    }
  }, [activeIndex]);

  return (
    <MainLayout>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-foreground">{t("learning.title")}</h1>
          <p className="text-muted-foreground mt-1 max-w-3xl">{t("learning.subtitle")}</p>
        </div>
        <Button
          type="button"
          variant="default"
          size="sm"
          className="shrink-0 self-end sm:self-start"
          onClick={() => navigate("/")}
        >
          <ArrowLeft className="w-4 h-4" />
          {t("learning.back")}
        </Button>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 lg:items-stretch">
        <aside className="order-2 lg:order-1 w-full lg:w-80 shrink-0 flex flex-col min-h-0">
          <h2 className="text-sm font-semibold text-foreground mb-2 lg:mb-3">
            {t("learning.playlist")}
          </h2>
          <ScrollArea className="lg:flex-1 lg:max-h-[min(70vh,560px)] rounded-lg border border-border bg-card/30">
            <ul className="p-2 space-y-1">
              {TRAINING_VIDEO_PLAYLIST.map((item, index) => (
                <li key={item.id}>
                  <Button
                    type="button"
                    variant={index === activeIndex ? "secondary" : "ghost"}
                    className={cn(
                      "w-full justify-start h-auto py-3 px-3 text-left font-normal",
                      index === activeIndex && "bg-secondary"
                    )}
                    onClick={() => handleSelect(index)}
                  >
                    <PlayCircle
                      className={cn(
                        "w-4 h-4 mr-2 shrink-0 mt-0.5",
                        index === activeIndex ? "text-primary" : "text-muted-foreground"
                      )}
                    />
                    <span className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium text-foreground leading-tight">
                        {t(item.titleKey)}
                      </span>
                      <span className="text-xs text-muted-foreground leading-snug">
                        {t(item.descriptionKey)}
                      </span>
                    </span>
                  </Button>
                </li>
              ))}
            </ul>
          </ScrollArea>
        </aside>

        <div className="order-1 lg:order-2 flex-1 min-w-0 flex flex-col gap-3">
          <div className="rounded-xl border border-border bg-black/90 overflow-hidden shadow-sm flex justify-center">
            <video
              key={active.src}
              ref={videoRef}
              className="w-full h-auto max-h-[min(72vh,800px)] block bg-black"
              controls
              playsInline
              preload="metadata"
              src={active.src}
              onError={() => {
                setVideoError(true);
                playWhenLoadedRef.current = false;
              }}
              onLoadedData={(e) => {
                setVideoError(false);
                if (!playWhenLoadedRef.current) return;
                playWhenLoadedRef.current = false;
                void e.currentTarget.play().catch(() => {});
              }}
            >
              {t("learning.videoNoHtml5")}
            </video>
          </div>
          <div className="lg:hidden">
            <p className="text-sm font-medium text-foreground">{t(active.titleKey)}</p>
            <p className="text-sm text-muted-foreground">{t(active.descriptionKey)}</p>
          </div>
          {videoError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{t("learning.videoLoadError")}</AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </MainLayout>
  );
}
