import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { apiPostNoAuth, getVisitorKey } from "@/lib/api";
import { Header } from "@/components/landing/Header";
import { Hero } from "@/components/landing/Hero";
import { ChartPreviewBlock } from "@/components/landing/ChartPreviewBlock";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Testimonials } from "@/components/landing/Testimonials";
import { FAQ } from "@/components/landing/FAQ";
import { CtaGreenBlock } from "@/components/landing/CtaGreenBlock";
import { Footer } from "@/components/landing/Footer";
import { PromoTrialDialog } from "@/components/landing/PromoTrialDialog";
import { AuthDialog } from "./Auth";

/**
 * Лендинг (маркетинговая страница).
 * Структура сверстана по типовому макету; точные тексты, отступы и ассеты — см. TODO в компонентах (Figma).
 */
export type AuthTab = 'signin' | 'signup';

export default function Landing() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [authOpen, setAuthOpen] = useState(false);
  const [authDefaultTab, setAuthDefaultTab] = useState<AuthTab>('signin');
  const [promoOpen, setPromoOpen] = useState(false);

  const openAuth = (tab: AuthTab = 'signin') => {
    setAuthDefaultTab(tab);
    setAuthOpen(true);
  };

  const openPromo = () => setPromoOpen(true);
  const handlePromoTryFree = () => {
    setPromoOpen(false);
    openAuth('signup');
  };

  // Учёт визита на лендинг для воронки админки
  useEffect(() => {
    apiPostNoAuth("/api/track/landing-visit", { visitor_key: getVisitorKey() }).catch(() => {});
  }, []);

  // Открыть окно входа при переходе с ?auth=open (например после выхода)
  useEffect(() => {
    if (searchParams.get('auth') === 'open') {
      setAuthDefaultTab('signin');
      setAuthOpen(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header onOpenAuth={openAuth} onOpenPromo={openPromo} />
      <main className="flex-1">
        <Hero onOpenAuth={openAuth} onOpenPromo={openPromo} />
        <ChartPreviewBlock />
        <Features />
        <HowItWorks />
        <Testimonials />
        <FAQ />
        <CtaGreenBlock onOpenAuth={openAuth} onOpenPromo={openPromo} />
      </main>
      <Footer />
      <PromoTrialDialog open={promoOpen} onOpenChange={setPromoOpen} onTryFree={handlePromoTryFree} />
      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} defaultTab={authDefaultTab} />
    </div>
  );
}
