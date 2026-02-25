import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { ChartPreviewBlock } from "@/components/landing/ChartPreviewBlock";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { CtaGreenBlock } from "@/components/landing/CtaGreenBlock";
import { Footer } from "@/components/landing/Footer";
import { AuthDialog } from "./Auth";

/**
 * Лендинг (маркетинговая страница).
 * Структура сверстана по типовому макету; точные тексты, отступы и ассеты — см. TODO в компонентах (Figma).
 */
export default function Landing() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [authOpen, setAuthOpen] = useState(false);

  // Открыть окно входа при переходе с ?auth=open (например после выхода)
  useEffect(() => {
    if (searchParams.get('auth') === 'open') {
      setAuthOpen(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header onOpenAuth={() => setAuthOpen(true)} />
      <main className="flex-1">
        <Hero onOpenAuth={() => setAuthOpen(true)} />
        <ChartPreviewBlock />
        <Features />
        <HowItWorks />
        <Testimonials />
        <FAQ />
        <CtaGreenBlock onOpenAuth={() => setAuthOpen(true)} />
      </main>
      <Footer />
      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} />
    </div>
  );
}
